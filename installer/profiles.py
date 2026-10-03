from pathlib import Path

from installer import manifest
from installer.config import SAVED_PROFILE
from installer.shell import write_file

DIR_NAME = "profiles"  # next to the manifest, one <name>.yml per profile


class ProfileError(ValueError):
    pass


def directory(manifest_path: Path) -> Path:
    return manifest_path.parent / DIR_NAME


def label(name: str) -> str:
    return f"{DIR_NAME}/{name}.yml"


def names(directory: Path) -> list[str]:
    return sorted(path.stem for path in directory.glob("*.yml"))


def listing(available: list[str]) -> str:
    if not available:
        return f"no profiles in {DIR_NAME}/"
    return f"profiles in {DIR_NAME}/: {', '.join(available)}"


def unknown(name: str, available: list[str]) -> str:
    return f"unknown profile {name!r}; {listing(available)}"


def load(path: Path) -> dict:
    # an empty profile is valid and adds nothing
    return manifest.load(path, allow_empty=True)


def extends(name: str, data: dict) -> list[str]:
    value = data.get("extends")
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ProfileError(f"profile {name!r}: extends must be a profile name or a list of them")


def body(data: dict) -> dict:
    """The profile's manifest settings, without its extends."""
    return {key: value for key, value in data.items() if key != "extends"}


def chain(name: str, profiles: dict[str, dict]) -> list[str]:
    """The profiles to apply on top of the base, in order.

    Depth first: for each entry in extends its own chain, then the profile itself. A
    profile reached twice is applied once, at its first position.
    """
    available = sorted(profiles)
    if name not in profiles:
        raise ProfileError(unknown(name, available))
    order: list[str] = []

    def visit(current: str, path: list[str]) -> None:
        if current in path:
            cycle = [*path[path.index(current) :], current]
            raise ProfileError(f"extension cycle: {' → '.join(cycle)}")
        if current in order:
            return
        for parent in extends(current, profiles[current]):
            if parent not in profiles:
                raise ProfileError(f"profile {current!r} extends {unknown(parent, available)}")
            visit(parent, [*path, current])
        order.append(current)

    visit(name, [])
    return order


def describe(chain: list[str]) -> str:
    return " → ".join(["base", *chain])


def save(name: str, root: str) -> None:
    """Record the profile on the system installed under root."""
    path = Path(root + str(SAVED_PROFILE))
    path.parent.mkdir(parents=True, exist_ok=True)
    write_file(path, f"{name}\n")
