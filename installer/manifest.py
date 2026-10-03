from pathlib import Path

import yaml

PACKAGE_SECTIONS = ("pacstrap", "post_chroot", "packages", "aur_packages", "aur_helpers")
REPO_SECTIONS = ("pacstrap", "post_chroot", "packages")
AUR_SECTIONS = ("aur_packages", "aur_helpers")


class ManifestError(ValueError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys instead of keeping the last one."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                line = key_node.start_mark.line + 1
                raise ManifestError(f"line {line}: duplicate key {key!r}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load(path: Path | str) -> dict:
    try:
        data = yaml.load(Path(path).read_text(), Loader=UniqueKeyLoader)
    except OSError as e:
        raise ManifestError(f"cannot read: {e.strerror}") from None
    except yaml.MarkedYAMLError as e:
        line = e.problem_mark.line + 1 if e.problem_mark else "?"
        raise ManifestError(f"line {line}: invalid YAML: {e.problem}") from None
    except yaml.YAMLError as e:
        raise ManifestError(f"invalid YAML: {e}") from None
    if not isinstance(data, dict):
        raise ManifestError("expected a mapping at the top level")
    return data


def section(data: dict, name: str) -> list[str]:
    return [str(item) for item in data.get(name) or []]


def mappings(data: dict, name: str) -> list[dict]:
    return [dict(item) for item in data.get(name) or []]


def repo_name(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")


def managed_packages(data: dict, ucode: str | None = None) -> list[str]:
    names = {pkg for name in PACKAGE_SECTIONS for pkg in section(data, name)}
    if ucode:
        names.add(ucode)
    names.update(item["name"] for item in mappings(data, "url_packages"))
    return sorted(names)
