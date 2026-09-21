import os
from pathlib import Path

from installer import paths
from installer.config import Config
from installer.pacstrap import pacstrap
from installer.partitions import create_partitions
from installer.shell import echo, run

MNT = "/mnt"


def install(cfg: Config, data: dict) -> None:
    chroot_repo = Path("/opt") / cfg.install_repo
    target = Path(MNT + str(chroot_repo))
    uv = ("uv", "--directory", str(chroot_repo))
    # the outer `uv run` exports VIRTUAL_ENV, which the inner uv would warn about
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}

    def chroot(step: str, user: str | None = None) -> None:
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
            env=env,
        )

    echo("==> Creating partitions...")
    create_partitions(cfg)

    echo("==> Installing base system...")
    pacstrap(cfg, data)

    # /tmp is avoided because arch-chroot mounts a tmpfs over it
    run("cp", "-r", str(paths.REPO_ROOT), str(target))
    # the venv from the live ISO is rebuilt against the pacstrapped Python
    run("rm", "-rf", str(target / ".venv"))
    run("arch-chroot", MNT, *uv, "sync", "--frozen", env=env)

    echo("==> Running post-chroot setup...")
    chroot("post-chroot")

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
