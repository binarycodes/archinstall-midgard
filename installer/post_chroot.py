from pathlib import Path

from installer import manifest, paths
from installer.config import BASE_SERVICES, USER_GROUPS, USER_SHELL, Config
from installer.shell import run, write_file


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


def configure_hostname(hostname: str) -> None:
    write_file("/etc/hostname", f"{hostname}\n")


def install_packages(data: dict) -> None:
    run("pacman", "--noconfirm", "-S", *manifest.section(data, "post_chroot"))
    run("mkinitcpio", "-P")


def enable_services() -> None:
    for service in BASE_SERVICES:
        run("systemctl", "enable", service)


def create_user(cfg: Config) -> None:
    # install sets the passwords collected up front once this step is done
    run("useradd", "-m", "-G", ",".join(USER_GROUPS), "-s", USER_SHELL, cfg.username)


def post_chroot(cfg: Config, data: dict, hostname: str) -> None:
    copy_configs()
    configure_time(cfg)
    configure_locale(cfg)
    configure_hostname(hostname)
    install_packages(data)
    enable_services()
    create_user(cfg)
