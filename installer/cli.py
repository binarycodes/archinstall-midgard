import functools
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape

from installer import cpu, disk, hardware, machine, memory, paths, profiles
from installer import hostname as hostnames
from installer.annotate import annotate
from installer.boot import create_boot_entries
from installer.cleanup import cleanup
from installer.config import METADATA, Config
from installer.customize import customize
from installer.daily import daily
from installer.install import install
from installer.packages import packages
from installer.post_chroot import post_chroot
from installer.projects import user_projects
from installer.shell import console, err_console, require_root, require_user
from installer.validate import check_aur_packages, check_repo_packages, skipped_checks

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


def fail(problems: list[str]) -> None:
    typer.echo(f"{len(problems)} problem(s):", err=True)
    for problem in problems:
        typer.echo(f"  {problem}", err=True)
    raise typer.Exit(1)


def check_files(path: Path, profile: str | None = None) -> machine.Files:
    """The manifest at path and its profiles (all, or just profile), or exit listing problems."""
    files = machine.read(path)
    problems = machine.check(files, [profile] if profile else files.available)
    if problems:
        fail(problems)
    return files


def load() -> tuple[Config, dict]:
    """The manifest for the profile this system was installed with, or exit."""
    try:
        loaded = machine.load_saved(paths.MANIFEST, METADATA, hardware.detect_features())
    except machine.MachineError as e:
        fail(e.problems)
    return loaded.cfg, loaded.data


HostnameOption = Annotated[str, typer.Option("--hostname", help="hostname of the new system")]
ProfileOption = Annotated[
    str | None,
    typer.Option(
        "--profile",
        help="profile in profiles/ to install, fixed for the life of the system; "
        "without it, the base manifest is installed",
    ),
]


@command("install", "full install from the live ISO (root)", root=True)
def install_cmd(hostname: HostnameOption, profile: ProfileOption = None) -> None:
    install(hostname, profile)


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
    files = check_files(manifest)
    directory = profiles.directory(manifest)
    features = manifest.parent / machine.FEATURES_DIR
    annotate(
        [
            manifest,
            *(directory / f"{name}.yml" for name in files.available),
            *(features / f"{name}.yml" for name in files.features),
        ]
    )


@command("validate", "check the manifest, every profile and feature file for mistakes", root=None)
def validate_cmd(
    manifest: Annotated[Path, typer.Argument()] = paths.MANIFEST,
    profile: Annotated[
        str | None, typer.Option("--profile", help="check only this profile")
    ] = None,
    packages: Annotated[
        bool,
        typer.Option(
            "-p",
            "--packages",
            help="also check every package exists in the repos or on the AUR (needs pacman, network)",
        ),
    ] = False,
) -> None:
    files = check_files(manifest, profile)
    for note in skipped_checks():
        typer.echo(f"note: {note}", err=True)
    names = [profile] if profile else files.available
    chains = {None: [], **{name: profiles.chain(name, files.profiles) for name in names}}
    if packages:
        # every package any of these profiles can install on any machine, looked up once
        data = machine.merged(files, machine.reachable(files, names), list(hardware.FEATURES))
        problems = check_repo_packages(data) + check_aur_packages(data)
        if problems:
            fail(problems)
    for name, chain in chains.items():
        typer.echo(f"{machine.checked_label(name, chain)}: ok")


@command("post-chroot", "install step: system configuration (root, in chroot)", root=True)
def post_chroot_cmd(hostname: HostnameOption) -> None:
    if problem := hostnames.problem(hostname):
        raise typer.BadParameter(problem, param_hint="--hostname")
    post_chroot(*load(), hostname)


@command("boot-entries", "install step: EFI boot entries (root, in chroot)", root=True)
def boot_entries_cmd() -> None:
    load()
    create_boot_entries()


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
    features: Annotated[
        bool, typer.Option("-f", "--features", help="every known hardware feature, detected or not")
    ] = False,
    list_profiles: Annotated[
        bool, typer.Option("-p", "--profiles", help="the profiles available to install")
    ] = False,
    select_disk: Annotated[
        bool,
        typer.Option(
            "-d", "--disk", help="dry run of the install's disk selection; changes nothing"
        ),
    ] = False,
    chain: Annotated[
        str | None,
        typer.Option(
            "-c", "--chain", metavar="PROFILE", help="the profile chain PROFILE resolves to"
        ),
    ] = None,
) -> None:
    if not (ucode or ram or swap or features or list_profiles or select_disk or chain):
        raise typer.BadParameter(
            "pass at least one check, e.g. -u, -r, -s, -f, -p, -d or -c PROFILE"
        )
    if ucode:
        typer.echo(cpu.ucode() or "none (CPU vendor has no microcode package)")
    if ram:
        typer.echo(f"{memory.total_gib():.1f} GiB")
    if swap:
        typer.echo(f"{memory.swap_gib(memory.total_gib())} GiB")
    if features:
        detected = hardware.detect_features()
        for name in hardware.FEATURES:
            typer.echo(f"{name}: {'yes' if name in detected else 'no'}")
    if list_profiles:
        available = profiles.names(profiles.directory(paths.MANIFEST))
        typer.echo("\n".join(available) or f"none (no files in {profiles.DIR_NAME}/)")
    if select_disk:
        swap_gib = memory.swap_gib(memory.total_gib())
        try:
            chosen = disk.select_disk(swap_gib)
        except disk.DiskError as e:
            err_console.print(f"\n[bold red]Disk selection aborted:[/] {escape(str(e))}")
            raise typer.Exit(1) from None
        console.print(
            f"\n[bold green]Dry run:[/] install would erase {chosen.path} as shown above. "
            "Nothing was changed."
        )
    if chain:
        try:
            typer.echo(profiles.describe(machine.chain(chain, paths.MANIFEST)))
        except machine.MachineError as e:
            fail(e.problems)


def main() -> None:
    app()
