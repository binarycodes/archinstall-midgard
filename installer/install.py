import os
import socket
import sys
from pathlib import Path

from rich.markup import escape

from installer import hardware, machine, manifest, memory, metadata, paths
from installer import hostname as hostnames
from installer.config import CHROOT_REPO_DIR, MNT, NETWORK_CHECK
from installer.pacstrap import pacstrap
from installer.partitions import create_partitions
from installer.shell import console, echo, err_console, run
from installer.user_inputs import InputError, collect
from installer.validate import check_aur_packages, check_repo_packages

EFI_VARS = Path("/sys/firmware/efi")
# git fails instead of asking for credentials or a host key, so the install never stops to wait
NONINTERACTIVE_GIT = {"GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}


def network_reachable() -> bool:
    try:
        socket.create_connection(NETWORK_CHECK, timeout=5).close()
    except OSError:
        return False
    return True


def preflight(hostname: str, profile: str) -> list[str]:
    """Reasons the install can't start; checked before a disk is even offered."""
    problems = []
    if problem := hostnames.problem(hostname):
        problems.append(problem)
    # the profile exists and the manifest it merges to is valid
    problems += machine.check(machine.read(paths.MANIFEST), profile)
    # recorded in the metadata of the new system
    try:
        metadata.git_source(paths.REPO_ROOT)
    except metadata.MetadataError as e:
        problems.append(str(e))
    if not EFI_VARS.is_dir():
        problems.append("not booted in UEFI mode; boot entries are created with EFISTUB")
    if not network_reachable():
        host, port = NETWORK_CHECK
        problems.append(f"no network: cannot reach {host}:{port}, which pacstrap needs")
    if problems:
        return problems
    # these need a valid manifest and the network
    data = machine.load(profile, paths.MANIFEST, hardware.detect_features()).data
    problems += check_repo_packages(data) + check_aur_packages(data)
    problems += unreachable_repos(data)
    return problems


def unreachable_repos(data: dict) -> list[str]:
    """git_repos that can't be cloned without a prompt, so the install would fail on them."""
    env = {**os.environ, **NONINTERACTIVE_GIT}
    problems = []
    for url in manifest.section(data, "git_repos"):
        result = run(
            "git", "ls-remote", url, "HEAD", check=False, capture=True, quiet=True, env=env
        )
        if result.returncode != 0:
            problems.append(f"git_repos: cannot clone {url} without a prompt")
    return problems


def set_passwords(passwords: dict[str, str]) -> None:
    # through stdin, so the passwords never show up in arguments, the environment or a file
    text = "".join(f"{account}:{password}\n" for account, password in passwords.items())
    run("arch-chroot", MNT, "chpasswd", input=text)


def install(hostname: str, profile: str) -> None:
    problems = preflight(hostname, profile)
    if problems:
        err_console.print("[bold red]Cannot install:[/]")
        for problem in problems:
            err_console.print(f"  {escape(problem)}")
        sys.exit(1)

    loaded = machine.load(profile, paths.MANIFEST, hardware.detect_features())
    git_repo_url, git_commit_sha = metadata.git_source(paths.REPO_ROOT)
    cfg, data = loaded.cfg, loaded.data
    console.print(
        f"Installing as [bold]{hostname}[/] with profile [bold]{escape(loaded.describe())}[/]"
    )
    console.print(f"Detected features: {', '.join(loaded.features) or 'none'}\n")
    swap_gib = memory.swap_gib(memory.total_gib())
    # every input is collected before anything is changed, so the rest runs unattended
    try:
        inputs = collect(swap_gib, cfg.username)
    except InputError as e:
        err_console.print(f"\n[bold red]Install aborted:[/] {escape(str(e))}")
        sys.exit(1)
    console.print("\n[bold green]All input collected.[/] The install now runs without you.\n")

    chroot_repo = CHROOT_REPO_DIR / cfg.install_repo
    target = Path(MNT + str(chroot_repo))
    uv = ("uv", "--directory", str(chroot_repo))
    # the outer `uv run` exports VIRTUAL_ENV, which the inner uv would warn about
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"} | NONINTERACTIVE_GIT

    def chroot(step: str, *args: str, user: str | None = None) -> None:
        as_user = ("runuser", "-u", user, "--") if user else ()
        run(
            "arch-chroot",
            MNT,
            *as_user,
            *uv,
            "run",
            "--frozen",
            "--no-sync",
            "installer",
            step,
            *args,
            env=env,
        )

    echo("==> Creating partitions...")
    create_partitions(inputs.disk, swap_gib)

    echo("==> Installing base system...")
    pacstrap(cfg, data)
    installed = metadata.Metadata(
        profile, loaded.features, git_repo_url, git_commit_sha, metadata.now()
    )
    metadata.write(installed, MNT)

    # /tmp is avoided because arch-chroot mounts a tmpfs over it
    run("cp", "-r", str(paths.REPO_ROOT), str(target))
    # the venv from the live ISO is rebuilt against the pacstrapped Python
    run("rm", "-rf", str(target / ".venv"))
    run("arch-chroot", MNT, *uv, "sync", "--frozen", env=env)

    echo("==> Running post-chroot setup...")
    chroot("post-chroot", "--hostname", hostname)
    set_passwords(inputs.passwords)

    echo("==> Creating boot entries...")
    chroot("boot-entries")

    echo("==> Installing packages...")
    chroot("packages", user=cfg.username)

    echo("==> Setting up user projects...")
    chroot("user-projects", user=cfg.username)

    echo("==> Running user customizations...")
    chroot("customize", user=cfg.username)

    run("rm", "-rf", str(target))

    echo("==> Install complete. Reboot and enjoy.")
