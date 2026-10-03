from installer.config import (
    EFI_PARTITION,
    EFI_SIZE,
    EFI_TYPE,
    LINUX_TYPE,
    MNT,
    ROOT_PARTITION,
    SWAP_PARTITION,
    SWAP_TYPE,
    Config,
)
from installer.shell import run


def create_partitions(cfg: Config) -> None:
    # leftovers from a previous attempt
    run("swapoff", cfg.swap, check=False, capture=True)
    run("umount", "-R", MNT, check=False, capture=True)

    run("sgdisk", "--zap-all", cfg.disk)
    for number, size, type_code in (
        (EFI_PARTITION, f"+{EFI_SIZE}", EFI_TYPE),
        (SWAP_PARTITION, f"+{cfg.swap_size}", SWAP_TYPE),
        (ROOT_PARTITION, "0", LINUX_TYPE),
    ):
        run("sgdisk", "-n", f"{number}:0:{size}", "-t", f"{number}:{type_code}", cfg.disk)

    run("mkfs.fat", "-F32", cfg.efi)
    run("mkswap", cfg.swap)
    run("mkfs.btrfs", "-f", cfg.root)

    run("mount", cfg.root, MNT)
    run("mount", "--mkdir", cfg.efi, f"{MNT}/boot")
    run("swapon", cfg.swap)
