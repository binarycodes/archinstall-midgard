"""The manifest a machine is set up from.

The base manifest, then the file of each detected hardware feature in the fixed feature
order, then the profile chain; later wins.
"""

from dataclasses import dataclass
from pathlib import Path

from installer import manifest, profiles
from installer.config import Config
from installer.hardware import FEATURES
from installer.profiles import ProfileError
from installer.validate import validate, validate_feature, validate_profile

FEATURES_DIR = "features"  # next to the manifest, one <feature>.yml per feature that adds anything


class MachineError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Files:
    """The base manifest and every profile and feature file next to it, as loaded."""

    base_label: str
    base: dict | None  # None when it failed to load
    base_error: str | None
    profiles: dict[str, dict]  # name → data, for each profile file that loaded
    errors: dict[str, str]  # profile name → why its file failed to load
    available: list[str]  # every profile file, loaded or not
    features: dict[str, dict]  # feature file name → data, for each one that loaded
    feature_errors: dict[str, str]  # feature file name → why it failed to load


@dataclass(frozen=True)
class Machine:
    profile: str
    chain: list[str]
    features: list[str]  # detected on this machine
    cfg: Config
    data: dict

    def describe(self) -> str:
        return label(self.profile, self.chain)


def label(profile: str, chain: list[str]) -> str:
    return f"{profile} ({profiles.describe(chain)})"


def checked_label(profile: str, chain: list[str]) -> str:
    """label() for the merged result validate checks, which includes every feature file."""
    return f"{profile} ({' → '.join(['base', 'features', *chain])})"


def feature_label(name: str) -> str:
    return f"{FEATURES_DIR}/{name}.yml"


def load_dir(directory: Path) -> tuple[list[str], dict[str, dict], dict[str, str]]:
    """Names of the *.yml files in directory, their data, and why any failed to load."""
    names = profiles.names(directory)
    loaded, errors = {}, {}
    for name in names:
        try:
            loaded[name] = profiles.load(directory / f"{name}.yml")
        except manifest.ManifestError as e:
            errors[name] = str(e)
    return names, loaded, errors


def read(manifest_path: Path) -> Files:
    base, base_error = None, None
    try:
        base = manifest.load(manifest_path)
    except manifest.ManifestError as e:
        base_error = str(e)
    available, loaded, errors = load_dir(profiles.directory(manifest_path))
    _, features, feature_errors = load_dir(manifest_path.parent / FEATURES_DIR)
    return Files(
        manifest_path.name, base, base_error, loaded, errors, available, features, feature_errors
    )


def targets(files: Files, only: str | None) -> list[str]:
    return [only] if only is not None else files.available


def reachable(files: Files, names: list[str]) -> list[str]:
    """names and every profile they extend, directly or not; tolerates broken extends."""
    seen: set[str] = set()
    pending = list(names)
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        value = files.profiles.get(name, {}).get("extends")
        parents = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        pending += [parent for parent in parents if isinstance(parent, str)]
    return sorted(seen)


def file_problems(files: Files, only: str | None) -> list[str]:
    """Problems in the base manifest, every feature file and each profile file involved."""
    if files.base is None:
        problems = [f"{files.base_label}: {files.base_error}"]
    else:
        problems = [f"{files.base_label}: {p}" for p in validate(files.base)]
    for name, error in files.feature_errors.items():
        problems.append(f"{feature_label(name)}: {error}")
    for name, data in files.features.items():
        problems += [f"{feature_label(name)}: {p}" for p in validate_feature(name, data)]
    for name in reachable(files, targets(files, only)):
        if name in files.errors:
            problems.append(f"{profiles.label(name)}: {files.errors[name]}")
        elif name in files.profiles:
            data = files.profiles[name]
            problems += [
                f"{profiles.label(name)}: {p}" for p in validate_profile(data, files.available)
            ]
        # a name with no file is reported by the profile that extends it
    return problems


def merged(files: Files, chain: list[str], features: list[str]) -> dict:
    """The base, then each of features that has a file in the fixed order, then chain."""
    layers = [
        files.features[name] for name in FEATURES if name in features and name in files.features
    ]
    layers += [profiles.body(files.profiles[name]) for name in chain]
    return manifest.merge(files.base, *layers)


def check(files: Files, only: str | None = None) -> list[str]:
    """Every problem with the files and with the merged result of each profile (or only one).

    The base manifest is complete on its own. The merged results are only checked once
    every file involved is valid on its own, and with every feature file merged in: lists
    only grow, so a machine with fewer features can't have a problem this misses.
    """
    if only is not None and only not in files.available:
        return [profiles.unknown(only, files.available)]
    problems = file_problems(files, only)
    if problems:
        return problems
    for name in targets(files, only):
        try:
            chain = profiles.chain(name, files.profiles)
        except ProfileError as e:
            problems.append(f"{profiles.label(name)}: {e}")
            continue
        data = merged(files, chain, list(FEATURES))
        problems += [f"{checked_label(name, chain)}: {p}" for p in validate(data)]
    return problems


def chain(profile: str, manifest_path: Path) -> list[str]:
    """The chain profile resolves to, without validating the manifest it gives."""
    files = read(manifest_path)
    if profile not in files.available:
        raise MachineError([profiles.unknown(profile, files.available)])
    broken = [name for name in reachable(files, [profile]) if name in files.errors]
    if broken:
        raise MachineError([f"{profiles.label(name)}: {files.errors[name]}" for name in broken])
    try:
        return profiles.chain(profile, files.profiles)
    except ProfileError as e:
        raise MachineError([str(e)]) from None


def load(profile: str, manifest_path: Path, features: list[str]) -> Machine:
    """The base manifest with the detected features and profile's chain merged on, validated."""
    files = read(manifest_path)
    problems = check(files, profile)
    if problems:
        raise MachineError(problems)
    profile_chain = profiles.chain(profile, files.profiles)
    data = merged(files, profile_chain, features)
    return Machine(profile, profile_chain, features, Config.from_manifest(data), data)


def load_saved(manifest_path: Path, saved: Path, features: list[str]) -> Machine:
    """load() for the profile this system was installed with."""
    available = profiles.names(profiles.directory(manifest_path))
    try:
        profile = saved.read_text().strip()
    except OSError as e:
        listing = profiles.listing(available)
        raise MachineError([f"{saved}: cannot read: {e.strerror}; {listing}"]) from None
    if profile not in available:
        raise MachineError([f"{saved}: {profiles.unknown(profile, available)}"])
    return load(profile, manifest_path, features)
