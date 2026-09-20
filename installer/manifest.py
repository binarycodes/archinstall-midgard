from pathlib import Path

import yaml

PACKAGE_SECTIONS = ("pacstrap", "post_chroot", "packages", "aur_packages", "aur_helpers")


def load(path: Path | str) -> dict:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise TypeError(f"{path}: expected a mapping at the top level")
    return data


def section(data: dict, name: str) -> list[str]:
    return [str(item) for item in data.get(name) or []]


def mappings(data: dict, name: str) -> list[dict]:
    return [dict(item) for item in data.get(name) or []]


def managed_packages(data: dict) -> list[str]:
    names = {pkg for name in PACKAGE_SECTIONS for pkg in section(data, name)}
    names.update(item["name"] for item in mappings(data, "url_packages"))
    return sorted(names)
