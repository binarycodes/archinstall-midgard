import json
import re
import shutil
import urllib.parse
import urllib.request
from dataclasses import fields
from pathlib import Path

from installer import manifest, profiles
from installer.annotate import describe
from installer.config import Config
from installer.manifest import AUR_SECTIONS, PACKAGE_SECTIONS, REPO_SECTIONS

CONFIG_KEYS = tuple(f.name for f in fields(Config))
SERVICE_SECTIONS = ("system_services", "user_services")
KNOWN_KEYS = (
    *CONFIG_KEYS,
    *PACKAGE_SECTIONS,
    *SERVICE_SECTIONS,
    "url_packages",
    "pacman_keys",
    "gsettings",
    "git_repos",
)
PROFILE_KEYS = (*KNOWN_KEYS, "extends")

# Arch package naming rules: lowercase alphanumerics and @._+-, not starting with - or .
PACKAGE_NAME = re.compile(r"^[a-z0-9@_+][a-z0-9@._+-]*$")
FINGERPRINT = re.compile(r"^[0-9A-Fa-f]{40}$")
GIT_URL = re.compile(r"^(https://|ssh://|git@)\S+$")

LOCALES = Path("/usr/share/i18n/SUPPORTED")
ZONEINFO = Path("/usr/share/zoneinfo")
AUR_RPC = "https://aur.archlinux.org/rpc/v5/info"


def validate(data: dict) -> list[str]:
    """Every problem in the manifest, as "key.path: message"; empty when it is valid."""
    problems = unknown_keys(data, KNOWN_KEYS)
    return problems + check_sections(data, complete=True)


def validate_profile(data: dict, available: list[str]) -> list[str]:
    """Every problem in one profile file on its own; available is every profile name.

    Every key is optional: a profile only overrides or adds to the self-sufficient base.
    """
    problems = unknown_keys(data, PROFILE_KEYS)
    problems += check_extends(data, available)
    return problems + check_sections(data, complete=False)


def unknown_keys(data: dict, known: tuple[str, ...]) -> list[str]:
    return [f"{key}: unknown key" for key in data if key not in known]


def check_sections(data: dict, complete: bool) -> list[str]:
    problems = check_config(data, complete)
    problems += check_packages(data)
    problems += check_services(data)
    problems += check_url_packages(data)
    problems += check_pacman_keys(data)
    problems += check_gsettings(data)
    problems += check_git_repos(data, complete)
    problems += check_system(data)
    return problems


def skipped_checks() -> list[str]:
    """Checks that need data files missing on this machine (e.g. in CI)."""
    notes = []
    if not LOCALES.is_file():
        notes.append(f"locale not checked: {LOCALES} not found")
    if not ZONEINFO.is_dir():
        notes.append(f"timezone not checked: {ZONEINFO} not found")
    return notes


def string_list(data: dict, key: str) -> tuple[list[tuple[str, str]], list[str]]:
    """(path, value) pairs for a list-of-strings section, and problems with its shape."""
    value = data.get(key)
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], [f"{key}: must be a list"]
    items, problems = [], []
    for i, item in enumerate(value):
        if isinstance(item, str) and item:
            items.append((f"{key}[{i}]", item))
        else:
            problems.append(f"{key}[{i}]: must be a non-empty string")
    return items, problems


def mapping_list(data: dict, key: str) -> tuple[list[tuple[str, dict]], list[str]]:
    value = data.get(key)
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], [f"{key}: must be a list"]
    items, problems = [], []
    for i, item in enumerate(value):
        if isinstance(item, dict):
            items.append((f"{key}[{i}]", item))
        else:
            problems.append(f"{key}[{i}]: must be a mapping")
    return items, problems


def check_extends(data: dict, available: list[str]) -> list[str]:
    value = data.get("extends")
    if isinstance(value, str) and value:
        items, problems = [("extends", value)], []
    elif value is None or isinstance(value, list):
        items, problems = string_list(data, "extends")
    else:
        return ["extends: must be a profile name or a list of profile names"]
    for path, name in items:
        if name not in available:
            problems.append(f"{path}: {profiles.unknown(name, available)}")
    return problems


def check_config(data: dict, complete: bool = True) -> list[str]:
    problems = []
    for key in CONFIG_KEYS:
        value = data.get(key)
        if value is None:
            if complete:
                problems.append(f"{key}: missing")
        elif not isinstance(value, str) or not value:
            problems.append(f"{key}: must be a non-empty string")
    return problems


def check_packages(data: dict) -> list[str]:
    problems = []
    first_seen: dict[str, str] = {}

    def add(path: str, name: str) -> None:
        if not PACKAGE_NAME.match(name):
            problems.append(f"{path}: {name!r} is not a valid package name")
        if name in first_seen:
            problems.append(f"{path}: {name!r} is already listed at {first_seen[name]}")
        else:
            first_seen[name] = path

    for key in PACKAGE_SECTIONS:
        items, shape = string_list(data, key)
        problems += shape
        for path, name in items:
            add(path, name)

    url_items, _ = mapping_list(data, "url_packages")
    for path, item in url_items:
        if isinstance(item.get("name"), str) and item["name"]:
            add(f"{path}.name", item["name"])
    return problems


def check_services(data: dict) -> list[str]:
    problems = []
    for key in SERVICE_SECTIONS:
        items, shape = string_list(data, key)
        problems += shape
        seen: dict[str, str] = {}
        for path, name in items:
            if name in seen:
                problems.append(f"{path}: {name!r} is already listed at {seen[name]}")
            seen.setdefault(name, path)
    return problems


def check_mapping_keys(path: str, item: dict, required: tuple[str, ...]) -> list[str]:
    problems = [f"{path}.{key}: unknown key" for key in item if key not in required]
    for key in required:
        if not isinstance(item.get(key), str) or not item[key]:
            problems.append(f"{path}.{key}: must be a non-empty string")
    return problems


def check_url_packages(data: dict) -> list[str]:
    items, problems = mapping_list(data, "url_packages")
    for path, item in items:
        problems += check_mapping_keys(path, item, ("name", "url"))
        url = item.get("url")
        if isinstance(url, str) and url and not url.startswith("https://"):
            problems.append(f"{path}.url: must start with https://")
    return problems


def check_pacman_keys(data: dict) -> list[str]:
    items, problems = mapping_list(data, "pacman_keys")
    for path, item in items:
        problems += check_mapping_keys(path, item, ("key", "server"))
        key = item.get("key")
        if isinstance(key, str) and key and not FINGERPRINT.match(key):
            problems.append(f"{path}.key: must be a 40 character hex fingerprint")
    return problems


def check_gsettings(data: dict) -> list[str]:
    value = data.get("gsettings")
    if value is None:
        return []
    if not isinstance(value, dict):
        return ["gsettings: must be a mapping of schema to keys"]
    problems = []
    for schema, keys in value.items():
        if not isinstance(keys, dict):
            problems.append(f"gsettings.{schema}: must be a mapping of key to value")
            continue
        for key, setting in keys.items():
            if not isinstance(setting, str | int | float | bool):
                problems.append(f"gsettings.{schema}.{key}: must be a string, number or boolean")
    return problems


def check_git_repos(data: dict, complete: bool = True) -> list[str]:
    items, problems = string_list(data, "git_repos")
    for path, url in items:
        if not GIT_URL.match(url):
            problems.append(f"{path}: {url!r} is not a git URL (https://, ssh:// or git@)")
    install_repo = data.get("install_repo")
    names = {manifest.repo_name(url) for _, url in items}
    if complete and isinstance(install_repo, str) and install_repo and install_repo not in names:
        problems.append(f"git_repos: must include the install_repo {install_repo!r}")
    return problems


def supported_locales(text: str) -> set[str]:
    # Arch lists "en_US.UTF-8/UTF-8 \", Debian-based systems "en_US.UTF-8 UTF-8"
    return {line.split("/")[0].split()[0] for line in text.splitlines() if line.strip()}


def check_system(data: dict) -> list[str]:
    problems = []
    locale = data.get("locale")
    if (
        isinstance(locale, str)
        and locale
        and LOCALES.is_file()
        and locale not in supported_locales(LOCALES.read_text())
    ):
        problems.append(f"locale: {locale!r} is not a supported locale")
    timezone = data.get("timezone")
    if isinstance(timezone, str) and timezone and ZONEINFO.is_dir():
        zone = ZONEINFO / timezone
        if ".." in Path(timezone).parts or not zone.is_file():
            problems.append(f"timezone: {timezone!r} is not a known timezone")
    return problems


def check_repo_packages(data: dict) -> list[str]:
    """Packages in the repo sections that the sync repos don't have; needs pacman."""
    if not shutil.which("pacman"):
        return ["packages not checked against the repos: pacman not found"]
    wanted = {name: key for key in REPO_SECTIONS for name in manifest.section(data, key)}
    found = set(describe(sorted(wanted), flags=("-Si",)))
    missing = sorted(wanted.keys() - found)
    return [f"{wanted[name]}: {name!r} not found in the sync repos" for name in missing]


def aur_info(names: list[str]) -> set[str]:
    query = urllib.parse.urlencode([("arg[]", name) for name in names])
    with urllib.request.urlopen(f"{AUR_RPC}?{query}", timeout=30) as response:
        return {result["Name"] for result in json.load(response)["results"]}


def check_aur_packages(data: dict, lookup=aur_info) -> list[str]:
    """Packages in the AUR sections that the AUR doesn't have; needs network."""
    wanted = {name: key for key in AUR_SECTIONS for name in manifest.section(data, key)}
    if not wanted:
        return []
    # makepkg splits debug symbols into <name>-debug, which is not on the AUR itself
    base = {name: name.removesuffix("-debug") for name in wanted}
    try:
        found = lookup(sorted(set(wanted) | set(base.values())))
    except OSError as e:
        return [f"AUR packages not checked: {e}"]
    missing = [name for name in sorted(wanted) if name not in found and base[name] not in found]
    return [f"{wanted[name]}: {name!r} not found on the AUR" for name in missing]
