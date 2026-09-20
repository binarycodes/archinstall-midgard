import re
from pathlib import Path

from installer.config import Config
from installer.shell import echo, output, run

ARCH_LABEL = "Arch Linux"
KERNELS = (("Arch Linux", "linux"), ("Arch Linux LTS", "linux-lts"))
ENTRY = re.compile(r"^Boot([0-9A-F]{4})\*?\s+(.*)$")


def parse_entries(text: str) -> list[tuple[str, str]]:
    entries = []
    for line in text.splitlines():
        m = ENTRY.match(line)
        if m:
            entries.append((m.group(1), m.group(2).strip()))
    return entries


def arch_entries(entries: list[tuple[str, str]]) -> list[str]:
    return [num for num, label in entries if ARCH_LABEL in label]


def boot_order(entries: list[tuple[str, str]]) -> list[str]:
    regular = [n for n, label in entries if ARCH_LABEL in label and "LTS" not in label]
    lts = [n for n, label in entries if "Arch Linux LTS" in label]
    other = [n for n, label in entries if ARCH_LABEL not in label]
    return regular + lts + other


def kernel_options(ucode: str, kernel: str, root_uuid: str) -> str:
    return (
        f"initrd=\\{ucode}.img initrd=\\initramfs-{kernel}.img "
        f"root=UUID={root_uuid} rw quiet loglevel=3"
    )


def boot_files(ucode: str) -> list[str]:
    files = [f"/boot/vmlinuz-{kernel}" for _, kernel in KERNELS]
    files += [f"/boot/initramfs-{kernel}.img" for _, kernel in KERNELS]
    files.append(f"/boot/{ucode}.img")
    return files


def create_boot_entries(cfg: Config) -> None:
    root_uuid = output("blkid", cfg.root, "-s", "UUID", "-o", "value").strip()

    for num in arch_entries(parse_entries(output("efibootmgr"))):
        run("efibootmgr", "--delete-bootnum", "--bootnum", num)

    for label, kernel in KERNELS:
        run(
            "efibootmgr",
            "--create",
            "--disk",
            cfg.disk,
            "--part",
            "1",
            "--label",
            label,
            "--loader",
            f"/vmlinuz-{kernel}",
            "--unicode",
            kernel_options(cfg.ucode, kernel, root_uuid),
        )

    entries = parse_entries(output("efibootmgr"))
    run("efibootmgr", "-o", ",".join(boot_order(entries)))

    for file in boot_files(cfg.ucode):
        if not Path(file).is_file():
            echo(f"WARNING: {file} not found")

    if not arch_entries(entries):
        echo("WARNING: No Arch Linux boot entries found")
    else:
        echo("Boot entries:")
        run("efibootmgr")
