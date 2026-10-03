import os
import re
from pathlib import Path

from installer import manifest
from installer.manifest import PACKAGE_SECTIONS
from installer.shell import echo, output

SECTION = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*):")
LIST_ITEM = re.compile(r"^(?P<prefix>\s+- )(?P<pkg>[^\s#]+)")
FIELD = re.compile(r"^(?P<key>Name|Description)\s*:\s*(?P<value>.*)$")


def parse_descriptions(text: str) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    name = None
    for line in text.splitlines():
        m = FIELD.match(line)
        if not m:
            continue
        if m.group("key") == "Name":
            name = m.group("value").strip()
        elif name:
            descriptions.setdefault(name, m.group("value").strip().rstrip("."))
            name = None
    return descriptions


def annotate_lines(lines: list[str], descriptions: dict[str, str]) -> list[str]:
    result = []
    in_package_section = False
    for line in lines:
        m = SECTION.match(line)
        if m:
            in_package_section = m.group("name") in PACKAGE_SECTIONS
        item = LIST_ITEM.match(line)
        if in_package_section and item and item.group("pkg") in descriptions:
            line = f"{item.group('prefix')}{item.group('pkg')} # {descriptions[item.group('pkg')]}"
        result.append(line)
    return result


def describe(packages: list[str], flags: tuple[str, ...] = ("-Si", "-Qi")) -> dict[str, str]:
    env = {**os.environ, "LC_ALL": "C"}
    text = ""
    for flag in flags:
        # the argument list is every package in the manifest, too long to be worth echoing
        text += output("pacman", flag, *packages, check=False, quiet=True, env=env)
    return parse_descriptions(text)


def file_packages(path: Path) -> set[str]:
    # profiles can be empty
    data = manifest.load(path, allow_empty=True)
    return {pkg for name in PACKAGE_SECTIONS for pkg in manifest.section(data, name)}


def annotate(paths: list[Path]) -> None:
    """Rewrite the package descriptions in each file, looked up once for all of them."""
    packages = {path: file_packages(path) for path in paths}
    wanted = sorted(set().union(*packages.values()))
    echo(f"Looking up descriptions for {len(wanted)} packages")
    # pacman with no package arguments would list every package in the repos
    descriptions = describe(wanted) if wanted else {}
    for path in paths:
        lines = path.read_text().split("\n")
        path.write_text("\n".join(annotate_lines(lines, descriptions)))
        found = len(packages[path] & descriptions.keys())
        echo(f"Annotated {found} of {len(packages[path])} packages in {path}")
