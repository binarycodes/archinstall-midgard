import functools
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from installer import cpu, manifest, memory, paths
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
from installer.validate import check_aur_packages, check_repo_packages, skipped_checks, validate

app = typer.Typer(
    name="installer",
    help="Arch Linux install and maintenance",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def allow_any() -> None:
    pass


def command(name: str, help: str, *, root: bool | None) -> Callable[[Callable], Callable]:
    """Register a command that runs its privilege guard before doing anything else.

    root=None is for read-only commands that are safe as root or a regular user.
    """

    def register(f: Callable) -> Callable:
        @functools.wraps(f)
        def run(*args, **kwargs):
            run.guard()
            return f(*args, **kwargs)

        run.guard = allow_any if root is None else require_root if root else require_user
        return app.command(name, help=help)(run)

    return register


def fail(path: Path, problems: list[str]) -> None:
    typer.echo(f"{path}: {len(problems)} problem(s)", err=True)
    for problem in problems:
        typer.echo(f"  {problem}", err=True)
    raise typer.Exit(1)


def load_manifest(path: Path) -> dict:
    """The manifest at path, or exit listing every problem with it."""
    try:
        data = manifest.load(path)
    except manifest.ManifestError as e:
        fail(path, [str(e)])
    problems = validate(data)
    if problems:
        fail(path, problems)
    return data


def load() -> tuple[Config, dict]:
    data = load_manifest(paths.MANIFEST)
    return Config.from_manifest(data), data


@command("install", "full install from the live ISO (root)", root=True)
def install_cmd() -> None:
    install(*load())


@command("packages", "install packages, restore configs, enable services", root=False)
def packages_cmd() -> None:
    packages(load()[1])


@command("daily", "packages, user projects and customizations", root=False)
def daily_cmd() -> None:
    daily(*load())


@command("cleanup", "remove explicitly installed packages not in the manifest", root=False)
def cleanup_cmd() -> None:
    cleanup(load()[1])


@command("annotate", "rewrite package descriptions into the manifest", root=False)
def annotate_cmd(manifest: Annotated[Path, typer.Argument()] = paths.MANIFEST) -> None:
    load_manifest(manifest)
    annotate(manifest)


@command("validate", "check the manifest for mistakes", root=None)
def validate_cmd(
    manifest: Annotated[Path, typer.Argument()] = paths.MANIFEST,
    packages: Annotated[
        bool,
        typer.Option(
            "-p",
            "--packages",
            help="also check every package exists in the repos or on the AUR (needs pacman, network)",
        ),
    ] = False,
) -> None:
    data = load_manifest(manifest)
    for note in skipped_checks():
        typer.echo(f"note: {note}", err=True)
    if packages:
        problems = check_repo_packages(data) + check_aur_packages(data)
        if problems:
            fail(manifest, problems)
    typer.echo(f"{manifest}: ok")


@command("post-chroot", "install step: system configuration (root, in chroot)", root=True)
def post_chroot_cmd() -> None:
    post_chroot(*load())


@command("boot-entries", "install step: EFI boot entries (root, in chroot)", root=True)
def boot_entries_cmd() -> None:
    create_boot_entries(load()[0])


@command("user-projects", "install step: clone repos and stow dotfiles", root=False)
def user_projects_cmd() -> None:
    user_projects(*load())


@command("customize", "install step: apply the gsettings section of the manifest", root=False)
def customize_cmd() -> None:
    customize(load()[1])


@command("check", "print what the installer detects on this machine", root=None)
def check_cmd(
    ucode: Annotated[
        bool, typer.Option("-u", "--ucode", help="detected microcode package")
    ] = False,
    ram: Annotated[bool, typer.Option("-r", "--ram", help="detected RAM in GiB")] = False,
    swap: Annotated[
        bool, typer.Option("-s", "--swap", help="swap size for the detected RAM, in GiB")
    ] = False,
) -> None:
    if not (ucode or ram or swap):
        raise typer.BadParameter("pass at least one check, e.g. -u, -r or -s")
    if ucode:
        typer.echo(cpu.ucode() or "none (CPU vendor has no microcode package)")
    if ram:
        typer.echo(f"{memory.total_gib():.1f} GiB")
    if swap:
        typer.echo(f"{memory.swap_gib(memory.total_gib())} GiB")


def main() -> None:
    app()
