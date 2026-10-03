from installer.config import (
    EFI_GIB,
    EFI_PARTITION,
    EFI_TYPE,
    LINUX_TYPE,
    MNT,
    ROOT_PARTITION,
    SWAP_PARTITION,
    SWAP_TYPE,
)
from installer.disk import Disk
from installer.shell import run


def create_partitions(disk: Disk, swap_gib: int) -> None:
    # leftovers from a previous attempt
    for swap in disk.swaps():
        run("swapoff", swap, check=False, capture=True)
    run("umount", "-R", MNT, check=False, capture=True)

    run("sgdisk", "--zap-all", disk.path)
    for number, size, type_code in (
        (EFI_PARTITION, f"+{EFI_GIB}G", EFI_TYPE),
        (SWAP_PARTITION, f"+{swap_gib}G", SWAP_TYPE),
        (ROOT_PARTITION, "0", LINUX_TYPE),
    ):
        run("sgdisk", "-n", f"{number}:0:{size}", "-t", f"{number}:{type_code}", disk.path)

    run("mkfs.fat", "-F32", disk.efi)
    run("mkswap", disk.swap)
    run("mkfs.btrfs", "-f", disk.root)

    run("mount", disk.root, MNT)
    run("mount", "--mkdir", disk.efi, f"{MNT}/boot")
    run("swapon", disk.swap)
