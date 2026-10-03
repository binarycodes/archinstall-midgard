from pathlib import Path

from installer import cpu, manifest
from installer.config import MNT, Config
from installer.shell import append_file, output, run, write_file


def pacstrap(cfg: Config, data: dict) -> None:
    Path(MNT, "etc").mkdir(parents=True, exist_ok=True)
    write_file(f"{MNT}/etc/vconsole.conf", f"KEYMAP={cfg.keymap}\n")

    ucode = cpu.ucode()
    extra = [ucode] if ucode else []
    run("pacstrap", "-K", MNT, *manifest.section(data, "pacstrap"), *extra)

    append_file(f"{MNT}/etc/fstab", output("genfstab", "-U", MNT))
