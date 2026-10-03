import re
from pathlib import Path

from installer import cpu
from installer.config import ARCH_LABEL, EFI_PARTITION, KERNEL_OPTIONS, KERNELS, Config
from installer.shell import echo, output, run

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


def kernel_options(ucode: str | None, kernel: str, root_uuid: str) -> str:
    initrds = ([f"initrd=\\{ucode}.img"] if ucode else []) + [f"initrd=\\initramfs-{kernel}.img"]
    return " ".join(initrds) + f" root=UUID={root_uuid} {KERNEL_OPTIONS}"


def boot_files(ucode: str | None) -> list[str]:
    files = [f"/boot/vmlinuz-{kernel}" for _, kernel in KERNELS]
    files += [f"/boot/initramfs-{kernel}.img" for _, kernel in KERNELS]
    if ucode:
        files.append(f"/boot/{ucode}.img")
    return files


def create_boot_entries(cfg: Config) -> None:
    root_uuid = output("blkid", cfg.root, "-s", "UUID", "-o", "value").strip()
    ucode = cpu.ucode()

    for num in arch_entries(parse_entries(output("efibootmgr"))):
        run("efibootmgr", "--delete-bootnum", "--bootnum", num)

    for label, kernel in KERNELS:
        run(
            "efibootmgr",
            "--create",
            "--disk",
            cfg.disk,
            "--part",
            str(EFI_PARTITION),
            "--label",
            label,
            "--loader",
            f"/vmlinuz-{kernel}",
            "--unicode",
            kernel_options(ucode, kernel, root_uuid),
        )

    entries = parse_entries(output("efibootmgr"))
    run("efibootmgr", "-o", ",".join(boot_order(entries)))

    for file in boot_files(ucode):
        if not Path(file).is_file():
            echo(f"WARNING: {file} not found")

    if not arch_entries(entries):
        echo("WARNING: No Arch Linux boot entries found")
    else:
        echo("Boot entries:")
        run("efibootmgr")
