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
