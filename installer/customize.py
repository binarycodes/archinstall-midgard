import os
import tempfile

from installer.shell import run


def gsettings_entries(data: dict) -> list[tuple[str, str, str]]:
    """Flatten manifest `gsettings: {schema: {key: value}}` into (schema, key, value) triples."""
    entries = []
    for schema, keys in (data.get("gsettings") or {}).items():
        for key, value in (keys or {}).items():
            entries.append((str(schema), str(key), gvariant(value)))
    return entries


def gvariant(value: object) -> str:
    # YAML parses true/false into bool; gsettings only accepts them lowercase
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def gsettings_command(
    schema: str, key: str, value: str, private_bus: bool = False
) -> tuple[str, ...]:
    command = ("gsettings", "set", schema, key, value)
    return ("dbus-run-session", "--", *command) if private_bus else command


def customize(data: dict) -> None:
    entries = gsettings_entries(data)
    if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        for entry in entries:
            run(*gsettings_command(*entry))
        return
    # The install chroot has no session bus, and runuser keeps root's
    # XDG_RUNTIME_DIR; dconf silently drops the write unless both are the user's.
    with tempfile.TemporaryDirectory() as runtime_dir:
        env = {**os.environ, "XDG_RUNTIME_DIR": runtime_dir}
        for entry in entries:
            run(*gsettings_command(*entry, private_bus=True), env=env)
