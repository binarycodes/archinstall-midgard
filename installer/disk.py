import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from rich import box
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from installer.config import (
    ARCHISO_MOUNTS,
    EFI_GIB,
    EFI_PARTITION,
    MIN_ROOT_GIB,
    MNT,
    ROOT_PARTITION,
    SWAP_PARTITION,
)
from installer.shell import console, output

LSBLK_COLUMNS = "NAME,PATH,TYPE,SIZE,MODEL,SERIAL,TRAN,RO,FSTYPE,LABEL,MOUNTPOINTS"
BY_ID = Path("/dev/disk/by-id")
SYS_BLOCK = Path("/sys/class/block")
GIB = 1024**3


class DiskError(Exception):
    pass


@dataclass(frozen=True)
class Partition:
    name: str
    path: str
    size: int
    fstype: str | None
    label: str | None
    mountpoints: tuple[str, ...]


@dataclass(frozen=True)
class Disk:
    name: str
    path: str
    size: int
    model: str
    serial: str
    tran: str
    read_only: bool = False
    fstype: str | None = None
    label: str | None = None
    mountpoints: tuple[str, ...] = ()
    partitions: tuple[Partition, ...] = ()
    by_id: str | None = None

    def partition(self, number: int) -> str:
        return partition_path(self.path, number)

    @property
    def efi(self) -> str:
        return self.partition(EFI_PARTITION)

    @property
    def swap(self) -> str:
        return self.partition(SWAP_PARTITION)

    @property
    def root(self) -> str:
        return self.partition(ROOT_PARTITION)

    @property
    def size_gib(self) -> float:
        return self.size / GIB

    def all_mountpoints(self) -> list[str]:
        return [*self.mountpoints, *(m for p in self.partitions for m in p.mountpoints)]

    def swaps(self) -> list[str]:
        return [p.path for p in self.partitions if "[SWAP]" in p.mountpoints]


def partition_path(disk: str, number: int) -> str:
    # The kernel inserts "p" only when the disk name ends in a digit
    # (nvme0n1p1, mmcblk0p1), never otherwise (sda1, vda1).
    separator = "p" if disk[-1].isdigit() else ""
    return f"{disk}{separator}{number}"


def mountpoints(device: dict) -> tuple[str, ...]:
    return tuple(m for m in device.get("mountpoints") or [] if m)


def parse_lsblk(text: str) -> list[Disk]:
    """Every disk in `lsblk -J -b` output, partitions included."""
    disks = []
    for device in json.loads(text)["blockdevices"]:
        if device.get("type") != "disk":
            continue
        partitions = tuple(
            Partition(
                name=child["name"],
                path=child["path"],
                size=int(child.get("size") or 0),
                fstype=child.get("fstype"),
                label=child.get("label"),
                mountpoints=mountpoints(child),
            )
            for child in device.get("children") or []
            if child.get("type") == "part"
        )
        disks.append(
            Disk(
                name=device["name"],
                path=device["path"],
                size=int(device.get("size") or 0),
                model=(device.get("model") or "").strip(),
                serial=(device.get("serial") or "").strip(),
                tran=device.get("tran") or "",
                # older lsblk prints booleans as "0"/"1"
                read_only=device.get("ro") in (True, 1, "1"),
                fstype=device.get("fstype"),
                label=device.get("label"),
                mountpoints=mountpoints(device),
                partitions=partitions,
            )
        )
    return disks


def is_candidate(disk: Disk) -> bool:
    if disk.name.startswith("zram") or disk.read_only or disk.size == 0:
        return False
    # the live ISO's own medium
    return not any(m.startswith(ARCHISO_MOUNTS) for m in disk.all_mountpoints())


def stable_id(name: str, by_id: Path = BY_ID) -> str | None:
    """The most readable /dev/disk/by-id link to the disk, e.g. nvme-Samsung_SSD_980_<serial>."""
    if not by_id.is_dir():
        return None
    links = [
        link for link in by_id.iterdir() if "-part" not in link.name and link.resolve().name == name
    ]
    # wwn- and eui. names are opaque; prefer the ones built from model and serial
    links.sort(key=lambda link: (link.name.startswith(("wwn-", "nvme-eui.")), link.name))
    return str(links[0]) if links else None


def candidates() -> list[Disk]:
    text = output("lsblk", "-J", "-b", "-o", LSBLK_COLUMNS, quiet=True)
    return [
        replace(disk, by_id=stable_id(disk.name))
        for disk in parse_lsblk(text)
        if is_candidate(disk)
    ]


def gib(size: float) -> str:
    return f"{size:.1f} GiB"


def min_size_gib(swap_gib: int) -> int:
    return EFI_GIB + swap_gib + MIN_ROOT_GIB


def problems(disk: Disk, swap_gib: int) -> list[str]:
    """Reasons the disk can't be installed to."""
    found = []
    if disk.size_gib < min_size_gib(swap_gib):
        found.append(
            f"{disk.path} is {gib(disk.size_gib)}; at least {min_size_gib(swap_gib)} GiB is "
            f"needed ({EFI_GIB} EFI + {swap_gib} swap + {MIN_ROOT_GIB} root)"
        )
    # mounts under the install target and swap are leftovers from an earlier attempt,
    # which the install clears before partitioning
    in_use = [
        m
        for m in disk.all_mountpoints()
        if m not in ("[SWAP]", MNT) and not m.startswith(f"{MNT}/")
    ]
    if in_use:
        found.append(f"{disk.path} is in use, mounted at {', '.join(in_use)}")
    return found


def table(title: str, *columns: str) -> Table:
    t = Table(title=title, title_justify="left", title_style="bold", box=box.SIMPLE_HEAD)
    for column in columns:
        t.add_column(column, overflow="fold")
    return t


def disks_table(disks: list[Disk]) -> Table:
    t = table("Disks", "#", "Device", "Size", "Model", "Bus", "Serial")
    t.columns[0].style = "bold cyan"
    t.columns[0].justify = t.columns[2].justify = "right"
    t.columns[5].style = "dim"
    for number, disk in enumerate(disks, start=1):
        t.add_row(
            str(number),
            disk.path,
            gib(disk.size_gib),
            escape(disk.model or "-"),
            disk.tran or "-",
            escape(disk.serial or "-"),
        )
    return t


def details(disk: Disk) -> Panel:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim")
    grid.add_column()
    grid.add_row("Device", f"[bold]{disk.path}[/]")
    grid.add_row("By id", escape(disk.by_id or "none"))
    grid.add_row("Model", escape(f"{disk.model or 'unknown'} ({disk.tran or 'unknown bus'})"))
    grid.add_row("Size", gib(disk.size_gib))
    return Panel(grid, title="Selected disk", title_align="left", expand=False)


def contents_table(disk: Disk) -> Table:
    """What is on the disk now: one row per partition, plus any whole-disk filesystem."""
    t = table("Current contents", "Partition", "Size", "Filesystem", "Label", "Mounted at")
    t.columns[1].justify = "right"
    for entry in ([disk] if disk.fstype else []) + list(disk.partitions):
        t.add_row(
            entry.path,
            gib(entry.size / GIB),
            entry.fstype or "-",
            escape(entry.label or "-"),
            escape(", ".join(entry.mountpoints) or "-"),
        )
    if not t.rows:
        t.add_row("[dim]no partitions[/]", "", "", "", "")
    return t


def layout_table(disk: Disk, swap_gib: int) -> Table:
    t = table("New layout", "Partition", "Use", "Size", "Filesystem", "Mounted at")
    t.columns[2].justify = "right"
    root_gib = max(disk.size_gib - EFI_GIB - swap_gib, 0)
    t.add_row(disk.efi, "EFI", gib(EFI_GIB), "vfat", "/boot")
    t.add_row(disk.swap, "swap", gib(swap_gib), "swap", "-")
    t.add_row(disk.root, "root", f"~{gib(root_gib)}", "btrfs", "/")
    return t


def prompt(ask: Callable[[str], str], question: str) -> str:
    try:
        return ask(question).strip()
    except EOFError:
        return ""


def pick(disks: list[Disk], ask: Callable[[str], str]) -> Disk:
    console.print(disks_table(disks))
    while True:
        answer = prompt(
            ask, f"Install to which disk? [cyan]\\[1-{len(disks)}][/], [cyan]q[/] to quit: "
        )
        if answer.lower() in ("q", ""):
            raise DiskError("no disk selected")
        if answer.isdigit() and 1 <= int(answer) <= len(disks):
            return disks[int(answer) - 1]
        console.print(f"[yellow]Enter a number from 1 to {len(disks)}.[/]")


def select_disk(swap_gib: int, ask: Callable[[str], str] | None = None) -> Disk:
    """Have the user pick and confirm the disk to erase. The only way a disk is chosen."""
    ask = ask or console.input
    disks = candidates()
    if not disks:
        raise DiskError("no disks to install to")

    disk = pick(disks, ask)

    console.print()
    console.print(details(disk))
    console.print(contents_table(disk))
    console.print(layout_table(disk, swap_gib))

    found = problems(disk, swap_gib)
    if found:
        raise DiskError("; ".join(found))

    console.print(f"[bold red]Everything on {disk.path} will be erased.[/]")
    if prompt(ask, f'Type "[bold]{disk.name}[/]" to confirm: ') != disk.name:
        raise DiskError("not confirmed")
    return disk


def boot_partition() -> tuple[str, int]:
    """The disk and partition number of the EFI partition mounted at /boot."""
    source = output("findmnt", "-n", "-o", "SOURCE", "/boot", check=False).strip()
    if not source:
        raise DiskError("/boot is not mounted")
    name = Path(source).name
    parent = output("lsblk", "-n", "-d", "-o", "PKNAME", source).strip()
    number = int((SYS_BLOCK / name / "partition").read_text())
    return f"/dev/{parent}", number
