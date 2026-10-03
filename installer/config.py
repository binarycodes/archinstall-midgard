from dataclasses import dataclass, fields
from pathlib import Path

# Disk layout, created in this order on the disk chosen during install;
# root takes the rest of the disk
EFI_PARTITION = 1
SWAP_PARTITION = 2
ROOT_PARTITION = 3

EFI_GIB = 1  # mounted at /boot, so it holds the kernels and initramfs images
SWAP_SPARE_GIB = 1  # swap is RAM plus this, so a full RAM image fits when hibernating
MIN_ROOT_GIB = 32  # smallest root worth installing the full package set onto

EFI_TYPE = "ef00"
SWAP_TYPE = "8200"
LINUX_TYPE = "8300"

# Install target, and where the repo is copied inside it for the chroot steps
MNT = "/mnt"

# The live ISO mounts its own medium under here; that disk is never offered
ARCHISO_MOUNTS = "/run/archiso"
# Reached before partitioning to make sure pacstrap will be able to download
NETWORK_CHECK = ("archlinux.org", 443)
CHROOT_REPO_DIR = Path("/opt")

# EFISTUB boot entries, one per kernel; the first is the default
ARCH_LABEL = "Arch Linux"
KERNELS = (("Arch Linux", "linux"), ("Arch Linux LTS", "linux-lts"))
KERNEL_OPTIONS = "rw quiet loglevel=3"

# New system
BASE_SERVICES = ("systemd-networkd", "systemd-resolved", "sshd")
USER_GROUPS = ("wheel", "lp")  # wheel: sudo access, lp: printer access
USER_SHELL = "/usr/bin/zsh"
PROJECTS_DIR = "projects"  # under the user's home; the install repo is cloned here
# The profile chosen at install; every later command reads it, and it never changes
SAVED_PROFILE = Path("/etc/installer/profile")


@dataclass(frozen=True)
class Config:
    username: str
    timezone: str
    locale: str
    keymap: str
    install_repo: str

    @classmethod
    def from_manifest(cls, data: dict) -> "Config":
        # the manifest is validated on load, so every field is present
        return cls(**{f.name: str(data[f.name]) for f in fields(cls)})
