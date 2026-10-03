import os
import socket
import sys
from pathlib import Path

from rich.markup import escape

from installer import hostname as hostnames
from installer import memory, paths
from installer.config import CHROOT_REPO_DIR, MNT, NETWORK_CHECK, Config
from installer.disk import DiskError, select_disk
from installer.pacstrap import pacstrap
from installer.partitions import create_partitions
from installer.shell import console, echo, err_console, run

EFI_VARS = Path("/sys/firmware/efi")


def network_reachable() -> bool:
    try:
        socket.create_connection(NETWORK_CHECK, timeout=5).close()
    except OSError:
        return False
    return True


def preflight(hostname: str) -> list[str]:
    """Reasons the install can't start; checked before a disk is even offered."""
    problems = []
    if problem := hostnames.problem(hostname):
        problems.append(problem)
    if not EFI_VARS.is_dir():
        problems.append("not booted in UEFI mode; boot entries are created with EFISTUB")
    if not network_reachable():
        host, port = NETWORK_CHECK
        problems.append(f"no network: cannot reach {host}:{port}, which pacstrap needs")
    return problems


def install(cfg: Config, data: dict, hostname: str) -> None:
    # the manifest was validated when it was loaded
    problems = preflight(hostname)
    if problems:
        err_console.print("[bold red]Cannot install:[/]")
        for problem in problems:
            err_console.print(f"  {escape(problem)}")
        sys.exit(1)

    console.print(f"Installing as [bold]{hostname}[/]\n")
    swap_gib = memory.swap_gib(memory.total_gib())
    try:
        disk = select_disk(swap_gib)
    except DiskError as e:
        err_console.print(f"\n[bold red]Install aborted:[/] {escape(str(e))}")
        sys.exit(1)

    chroot_repo = CHROOT_REPO_DIR / cfg.install_repo
    target = Path(MNT + str(chroot_repo))
    uv = ("uv", "--directory", str(chroot_repo))
    # the outer `uv run` exports VIRTUAL_ENV, which the inner uv would warn about
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}

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
    create_partitions(disk, swap_gib)

    echo("==> Installing base system...")
    pacstrap(cfg, data)

    # /tmp is avoided because arch-chroot mounts a tmpfs over it
    run("cp", "-r", str(paths.REPO_ROOT), str(target))
    # the venv from the live ISO is rebuilt against the pacstrapped Python
    run("rm", "-rf", str(target / ".venv"))
    run("arch-chroot", MNT, *uv, "sync", "--frozen", env=env)

    echo("==> Running post-chroot setup...")
    chroot("post-chroot", "--hostname", hostname)

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
