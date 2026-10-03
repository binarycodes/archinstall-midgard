"""What a system was installed from, recorded in /etc like /etc/os-release."""

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from installer.config import METADATA
from installer.shell import output, write_file


class MetadataError(ValueError):
    pass


@dataclass(frozen=True)
class Metadata:
    profile: str
    features: list[str]
    git_repo_url: str
    git_commit_sha: str
    install_date: str  # UTC, ISO 8601

    def render(self) -> str:
        values = {
            "PROFILE": self.profile,
            "FEATURES": " ".join(self.features),
            "GIT_REPO_URL": self.git_repo_url,
            "GIT_COMMIT_SHA": self.git_commit_sha,
            "INSTALL_DATE": self.install_date,
        }
        return "".join(f"{key}={quote(value)}\n" for key, value in values.items())


ESCAPED = re.compile(r'\\([\\"$`])')


def quote(value: str) -> str:
    # double quotes with shell escapes, as os-release(5) describes
    for char in ("\\", '"', "$", "`"):
        value = value.replace(char, f"\\{char}")
    return f'"{value}"'


def parse(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            values[key] = unquote(value)
    return values


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return ESCAPED.sub(r"\1", value[1:-1])
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_source(repo: Path) -> tuple[str, str]:
    """The origin URL and HEAD commit of the repository the installer runs from."""
    git = ("git", "-C", str(repo))
    try:
        url = output(*git, "remote", "get-url", "origin", quiet=True).strip()
        sha = output(*git, "rev-parse", "HEAD", quiet=True).strip()
    except subprocess.CalledProcessError as e:
        reason = e.stderr.strip() or f"git exited with {e.returncode}"
        raise MetadataError(f"cannot read the git origin and commit of {repo}: {reason}") from None
    except OSError as e:
        raise MetadataError(f"cannot run git: {e.strerror}") from None
    return url, sha


def write(metadata: Metadata, root: str) -> None:
    """Record metadata on the system installed under root."""
    path = Path(root + str(METADATA))
    write_file(path, metadata.render())


def read(path: Path) -> dict[str, str]:
    return parse(path.read_text())
