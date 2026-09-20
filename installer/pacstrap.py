from pathlib import Path

from installer import manifest
from installer.config import Config
from installer.shell import append_file, output, run, write_file


def pacstrap(cfg: Config, data: dict) -> None:
    Path("/mnt/etc").mkdir(parents=True, exist_ok=True)
    write_file("/mnt/etc/vconsole.conf", f"KEYMAP={cfg.keymap}\n")

    run("pacstrap", "-K", "/mnt", *manifest.section(data, "pacstrap"))

    append_file("/mnt/etc/fstab", output("genfstab", "-U", "/mnt"))
