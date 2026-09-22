import argparse
from collections.abc import Callable
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

Step = Callable[[Config, dict, argparse.Namespace], None]


def add_command(
    sub: argparse._SubParsersAction, name: str, help: str, *, root: bool, step: Step
) -> argparse.ArgumentParser:
    p = sub.add_parser(name, help=help)
    p.set_defaults(guard=require_root if root else require_user, step=step)
    return p


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="installer", description="Arch Linux install and maintenance"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_command(
        sub,
        "install",
        "full install from the live ISO (root)",
        root=True,
        step=lambda c, d, a: install(c, d),
    )
    add_command(
        sub,
        "packages",
        "install packages, restore configs, enable services",
        root=False,
        step=lambda c, d, a: packages(d),
    )
    add_command(
        sub,
        "daily",
        "packages, user projects and customizations",
        root=False,
        step=lambda c, d, a: daily(c, d),
    )
    add_command(
        sub,
        "cleanup",
        "remove explicitly installed packages not in the manifest",
        root=False,
        step=lambda c, d, a: cleanup(d),
    )
    p = add_command(
        sub,
        "annotate",
        "rewrite package descriptions into the manifest",
        root=False,
        step=lambda c, d, a: annotate(a.manifest),
    )
    p.add_argument("manifest", nargs="?", type=Path, default=paths.MANIFEST)

    add_command(
        sub,
        "post-chroot",
        "install step: system configuration (root, in chroot)",
        root=True,
        step=lambda c, d, a: post_chroot(c, d),
    )
    add_command(
        sub,
        "boot-entries",
        "install step: EFI boot entries (root, in chroot)",
        root=True,
        step=lambda c, d, a: create_boot_entries(c),
    )
    add_command(
        sub,
        "user-projects",
        "install step: clone repos and stow dotfiles",
        root=False,
        step=lambda c, d, a: user_projects(c, d),
    )
    add_command(
        sub,
        "customize",
        "install step: apply the gsettings section of the manifest",
        root=False,
        step=lambda c, d, a: customize(d),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    data = manifest.load(paths.MANIFEST)
    cfg = Config.from_manifest(data)
    args.guard()
    args.step(cfg, data, args)
