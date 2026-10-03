import pytest

from installer import annotate

PACMAN_OUTPUT = """\
Repository      : core
Name            : iwd
Version         : 3.0-1
Description     : Internet Wireless Daemon.

Name            : vim
Description     : Vi Improved, a highly configurable, improved version of the vi text editor
Name            : vim
Description     : a duplicate that must not win
"""

MANIFEST = """\
---
pacstrap:
  - iwd
  - vim # stale text
  - unknown-pkg

system_services:
  - iwd
  - sshd
"""


def test_parse_descriptions_strips_trailing_dot_and_keeps_first():
    descs = annotate.parse_descriptions(PACMAN_OUTPUT)
    assert descs == {
        "iwd": "Internet Wireless Daemon",
        "vim": "Vi Improved, a highly configurable, improved version of the vi text editor",
    }


def test_annotate_rewrites_only_package_sections():
    descs = {"iwd": "Internet Wireless Daemon", "vim": "Vi Improved"}
    assert annotate.annotate_lines(MANIFEST.split("\n"), descs) == [
        "---",
        "pacstrap:",
        "  - iwd # Internet Wireless Daemon",
        "  - vim # Vi Improved",
        "  - unknown-pkg",
        "",
        "system_services:",
        "  - iwd",
        "  - sshd",
        "",
    ]


def test_annotate_rewrites_every_file_with_one_lookup(monkeypatch, tmp_path):
    base = tmp_path / "manifest.yml"
    base.write_text("packages:\n  - vim\n")
    profile = tmp_path / "gaming.yml"
    profile.write_text("extends: [a]\naur_packages:\n  - iwd # old\n")
    empty = tmp_path / "empty.yml"
    empty.write_text("")
    lookups = []

    def describe(packages):
        lookups.append(packages)
        return {"vim": "Vi Improved", "iwd": "Internet Wireless Daemon"}

    monkeypatch.setattr(annotate, "describe", describe)
    annotate.annotate([base, profile, empty])

    assert lookups == [["iwd", "vim"]]
    assert base.read_text() == "packages:\n  - vim # Vi Improved\n"
    assert (
        profile.read_text() == "extends: [a]\naur_packages:\n  - iwd # Internet Wireless Daemon\n"
    )
    assert empty.read_text() == ""


def test_annotate_skips_the_lookup_without_packages(monkeypatch, tmp_path):
    empty = tmp_path / "empty.yml"
    empty.write_text("")
    monkeypatch.setattr(annotate, "describe", lambda packages: pytest.fail("looked up"))
    annotate.annotate([empty])
