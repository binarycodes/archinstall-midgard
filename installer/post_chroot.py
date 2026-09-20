from pathlib import Path

from installer import manifest, paths
from installer.config import Config
from installer.shell import echo, run, write_file

BASE_SERVICES = ("systemd-networkd", "systemd-resolved", "iwd", "sshd")


def copy_configs() -> None:
    run("rsync", "-av", "--no-owner", "--no-group", f"{paths.CONFIG_DIR}/", "/")


def configure_time(cfg: Config) -> None:
    run("ln", "-sf", f"/usr/share/zoneinfo/{cfg.timezone}", "/etc/localtime")
    run("hwclock", "--systohc")


def uncomment_locale(text: str, locale: str) -> str:
    return "\n".join(line.replace(f"#{locale}", locale, 1) for line in text.split("\n"))


def configure_locale(cfg: Config) -> None:
    locale_gen = Path("/etc/locale.gen")
    write_file(locale_gen, uncomment_locale(locale_gen.read_text(), cfg.locale))
    run("locale-gen")
    write_file("/etc/locale.conf", f"LANG={cfg.locale}\n")
    write_file("/etc/vconsole.conf", f"KEYMAP={cfg.keymap}\n")


def configure_system(cfg: Config) -> None:
    write_file("/etc/hostname", f"{cfg.hostname}\n")


def install_packages(data: dict) -> None:
    run("pacman", "--noconfirm", "-S", *manifest.section(data, "post_chroot"))
    run("mkinitcpio", "-P")


def enable_services() -> None:
    for service in BASE_SERVICES:
        run("systemctl", "enable", service)


def create_user(cfg: Config) -> None:
    echo("set password for root")
    run("passwd")
    # wheel: sudo access, lp: printer access
    run("useradd", "-m", "-G", "wheel,lp", "-s", "/usr/bin/zsh", cfg.username)
    echo(f"set password for - {cfg.username}")
    run("passwd", cfg.username)


def post_chroot(cfg: Config, data: dict) -> None:
    copy_configs()
    configure_time(cfg)
    configure_locale(cfg)
    configure_system(cfg)
    install_packages(data)
    enable_services()
    create_user(cfg)
