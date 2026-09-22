import argparse
from pathlib import Path

from installer import manifest, paths
from installer.annotate import annotate
from installer.boot import create_boot_entries
from installer.cleanup import cleanup
from installer.config import Config
from installer.customize import customize
from installer.daily import daily
from installer.install import install
from installer.packages import packages
from installer.post_chroot import post_chroot
from installer.projects import user_projects
from installer.shell import require_root, require_user


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="installer", description="Arch Linux install and maintenance"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("install", help="full install from the live ISO (root)")
    sub.add_parser("packages", help="install packages, restore configs, enable services")
    sub.add_parser("daily", help="packages, user projects and customizations")
    sub.add_parser("cleanup", help="remove explicitly installed packages not in the manifest")
    p = sub.add_parser("annotate", help="rewrite package descriptions into the manifest")
    p.add_argument("manifest", nargs="?", type=Path, default=paths.MANIFEST)

    sub.add_parser("post-chroot", help="install step: system configuration (root, in chroot)")
    sub.add_parser("boot-entries", help="install step: EFI boot entries (root, in chroot)")
    sub.add_parser("user-projects", help="install step: clone repos and stow dotfiles")
    sub.add_parser("customize", help="install step: apply the gsettings section of the manifest")

    args = parser.parse_args(argv)
    data = manifest.load(paths.MANIFEST)
    cfg = Config.from_manifest(data)

    match args.command:
        case "install":
            require_root()
            install(cfg, data)
        case "post-chroot":
            require_root()
            post_chroot(cfg, data)
        case "boot-entries":
            require_root()
            create_boot_entries(cfg)
        case "packages":
            require_user()
            packages(data)
        case "user-projects":
            require_user()
            user_projects(cfg, data)
        case "customize":
            require_user()
            customize(data)
        case "daily":
            require_user()
            daily(cfg, data)
        case "cleanup":
            cleanup(data)
        case "annotate":
            annotate(args.manifest)
