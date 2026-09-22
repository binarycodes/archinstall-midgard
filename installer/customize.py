import os
import tempfile

from installer.shell import run

GSETTINGS = (
    ("org.gnome.desktop.interface", "color-scheme", "prefer-dark"),
    ("org.gnome.desktop.interface", "gtk-theme", "Adwaita-dark"),
    ("org.gnome.desktop.interface", "icon-theme", "Papirus"),
    ("org.gnome.desktop.interface", "font-name", "Roboto 12"),
)


def gsettings_command(
    schema: str, key: str, value: str, private_bus: bool = False
) -> tuple[str, ...]:
    command = ("gsettings", "set", schema, key, value)
    return ("dbus-run-session", "--", *command) if private_bus else command


def customize() -> None:
    if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        for entry in GSETTINGS:
            run(*gsettings_command(*entry))
        return
    # The install chroot has no session bus, and runuser keeps root's
    # XDG_RUNTIME_DIR; dconf silently drops the write unless both are the user's.
    with tempfile.TemporaryDirectory() as runtime_dir:
        env = {**os.environ, "XDG_RUNTIME_DIR": runtime_dir}
        for entry in GSETTINGS:
            run(*gsettings_command(*entry, private_bus=True), env=env)
