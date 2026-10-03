from dataclasses import dataclass, fields
from pathlib import Path

# Disk layout, created in this order on `disk`; root takes the rest of the disk
EFI_PARTITION = 1
SWAP_PARTITION = 2
ROOT_PARTITION = 3

EFI_SIZE = "1G"  # mounted at /boot, so it holds the kernels and initramfs images
SWAP_SPARE_GIB = 1  # swap is RAM plus this, so a full RAM image fits when hibernating

EFI_TYPE = "ef00"
SWAP_TYPE = "8200"
LINUX_TYPE = "8300"

# Install target, and where the repo is copied inside it for the chroot steps
MNT = "/mnt"
CHROOT_REPO_DIR = Path("/opt")

# EFISTUB boot entries, one per kernel; the first is the default
ARCH_LABEL = "Arch Linux"
KERNELS = (("Arch Linux", "linux"), ("Arch Linux LTS", "linux-lts"))
KERNEL_OPTIONS = "rw quiet loglevel=3"

# New system
BASE_SERVICES = ("systemd-networkd", "systemd-resolved", "iwd", "sshd")
USER_GROUPS = ("wheel", "lp")  # wheel: sudo access, lp: printer access
USER_SHELL = "/usr/bin/zsh"
PROJECTS_DIR = "projects"  # under the user's home; the install repo is cloned here


@dataclass(frozen=True)
class Config:
    username: str
    hostname: str
    timezone: str
    locale: str
    keymap: str
    install_repo: str
    disk: str

    @classmethod
    def from_manifest(cls, data: dict) -> "Config":
        # the manifest is validated on load, so every field is present
        return cls(**{f.name: str(data[f.name]) for f in fields(cls)})

    def partition(self, number: int) -> str:
        # The kernel inserts "p" only when the disk name ends in a digit
        # (nvme0n1p1, mmcblk0p1), never otherwise (sda1, vda1).
        separator = "p" if self.disk[-1].isdigit() else ""
        return f"{self.disk}{separator}{number}"

    @property
    def efi(self) -> str:
        return self.partition(EFI_PARTITION)

    @property
    def swap(self) -> str:
        return self.partition(SWAP_PARTITION)

    @property
    def root(self) -> str:
        return self.partition(ROOT_PARTITION)
