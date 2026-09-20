import shutil
import tempfile
from pathlib import Path

from installer import manifest, paths
from installer.shell import echo, run

YAY_FLAGS = ("--aur", "--answerclean", "None", "--answerdiff", "None", "--noconfirm", "--needed")


def install_packages(data: dict, name: str) -> None:
    packages = manifest.section(data, name)
    if not packages:
        echo(f"No packages found for section: {name}")
        return
    echo(f"Installing {name}...")
    run("sudo", "pacman", "--noconfirm", "--needed", "-S", *packages)


def import_pacman_keys(data: dict) -> None:
    for item in manifest.mappings(data, "pacman_keys"):
        echo(f"Importing key: {item['key']} from {item['server']}")
        run("sudo", "pacman-key", "--keyserver", item["server"], "--recv-keys", item["key"])
        run("sudo", "pacman-key", "--lsign-key", item["key"])


def install_url_packages(data: dict) -> None:
    items = manifest.mappings(data, "url_packages")
    if not items:
        echo("No URL packages found")
        return
    for item in items:
        echo(f"Installing URL package - {item['name']} ...")
        run("sudo", "pacman", "--noconfirm", "--needed", "-U", item["url"])


def install_aur_packages(data: dict, name: str) -> None:
    packages = manifest.section(data, name)
    if not packages:
        echo(f"No AUR packages found for section: {name}")
        return
    echo(f"Installing AUR {name}...")
    run("yay", "-S", *YAY_FLAGS, *packages)


def install_yay() -> None:
    if shutil.which("yay"):
        echo("yay already installed, skipping...")
        return
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir) / "yay-bin"
        run("git", "clone", "https://aur.archlinux.org/yay-bin.git", str(build_dir))
        run("makepkg", "-si", "--noconfirm", cwd=build_dir)


def restore_configs() -> None:
    # package installs may have overwritten files from config/
    run("sudo", "rsync", "-av", "--no-owner", "--no-group", f"{paths.CONFIG_DIR}/", "/")


def enable_services(data: dict, name: str, system: bool) -> None:
    cmd = ("sudo", "systemctl") if system else ("systemctl", "--user")
    for service in manifest.section(data, name):
        echo(f"Enabling {service}...")
        run(*cmd, "enable", service)


def packages(data: dict) -> None:
    run("sudo", "pacman", "-Syu", "--noconfirm")

    install_packages(data, "packages")

    install_yay()
    install_aur_packages(data, "aur_packages")
    import_pacman_keys(data)
    install_url_packages(data)

    restore_configs()

    enable_services(data, "system_services", system=True)
    enable_services(data, "user_services", system=False)

    # AUR updates need yay, so this comes last
    run("yay", "-Syu", *YAY_FLAGS)
