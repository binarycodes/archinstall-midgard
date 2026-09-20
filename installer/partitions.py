from installer.config import Config
from installer.shell import run

EFI_TYPE = "ef00"
SWAP_TYPE = "8200"
LINUX_TYPE = "8300"


def create_partitions(cfg: Config) -> None:
    # leftovers from a previous attempt
    run("swapoff", cfg.swap, check=False, capture=True)
    run("umount", "-R", "/mnt", check=False, capture=True)

    run("sgdisk", "--zap-all", cfg.disk)
    run("sgdisk", "-n", "1:0:+1G", "-t", f"1:{EFI_TYPE}", cfg.disk)
    run("sgdisk", "-n", f"2:0:+{cfg.swap_size}", "-t", f"2:{SWAP_TYPE}", cfg.disk)
    run("sgdisk", "-n", "3:0:0", "-t", f"3:{LINUX_TYPE}", cfg.disk)

    run("mkfs.fat", "-F32", cfg.efi)
    run("mkswap", cfg.swap)
    run("mkfs.btrfs", "-f", cfg.root)

    run("mount", cfg.root, "/mnt")
    run("mount", "--mkdir", cfg.efi, "/mnt/boot")
    run("swapon", cfg.swap)
