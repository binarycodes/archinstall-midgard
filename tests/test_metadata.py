import subprocess

import pytest

from installer import metadata
from installer.metadata import Metadata, MetadataError

RECORD = Metadata(
    "gaming",
    ["battery", "wifi", "gpu_amd"],
    "git@github.com:me/install.git",
    "0611c08aa0d6a0e9a8bd31c0e5e7c4b8f2d7e3a1",
    "2026-10-03T12:00:00Z",
)


def test_render_is_os_release_style():
    assert RECORD.render() == (
        'PROFILE="gaming"\n'
        'FEATURES="battery wifi gpu_amd"\n'
        'GIT_REPO_URL="git@github.com:me/install.git"\n'
        'GIT_COMMIT_SHA="0611c08aa0d6a0e9a8bd31c0e5e7c4b8f2d7e3a1"\n'
        'INSTALL_DATE="2026-10-03T12:00:00Z"\n'
    )


def test_render_without_features():
    record = Metadata("a", [], "u", "s", "d")
    assert 'FEATURES=""\n' in record.render()


def test_parse_round_trip():
    assert metadata.parse(RECORD.render()) == {
        "PROFILE": "gaming",
        "FEATURES": "battery wifi gpu_amd",
        "GIT_REPO_URL": "git@github.com:me/install.git",
        "GIT_COMMIT_SHA": "0611c08aa0d6a0e9a8bd31c0e5e7c4b8f2d7e3a1",
        "INSTALL_DATE": "2026-10-03T12:00:00Z",
    }


def test_quoting_round_trips_shell_characters():
    record = Metadata('a"b$c`d\\e', [], "u", "s", "d")
    assert metadata.parse(record.render())["PROFILE"] == 'a"b$c`d\\e'


def test_parse_ignores_comments_and_blank_lines():
    assert metadata.parse("# note\n\nPROFILE=plain\n") == {"PROFILE": "plain"}


def test_now_is_utc_iso_8601():
    assert len(metadata.now()) == len("2026-10-03T12:00:00Z")
    assert metadata.now().endswith("Z")


def test_write_goes_under_root(monkeypatch, tmp_path):
    monkeypatch.setattr(metadata, "write_file", lambda path, text: path.write_text(text))
    (tmp_path / "etc").mkdir()
    metadata.write(RECORD, str(tmp_path))
    assert (tmp_path / "etc" / "os-midgard-metadata").read_text() == RECORD.render()


def git(repo, *args):
    subprocess.run(("git", "-C", str(repo), *args), check=True, capture_output=True)


def test_git_source(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "remote", "add", "origin", "https://example.com/me/install.git")
    git(
        tmp_path,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "x",
    )
    url, sha = metadata.git_source(tmp_path)
    assert url == "https://example.com/me/install.git"
    assert len(sha) == 40


def test_git_source_without_origin(tmp_path):
    git(tmp_path, "init", "-q")
    with pytest.raises(MetadataError, match="cannot read the git origin and commit of .*origin"):
        metadata.git_source(tmp_path)
