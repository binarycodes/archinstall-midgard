import argparse

from installer import cli
from installer.shell import require_root, require_user

ROOT_COMMANDS = {"install", "post-chroot", "boot-entries"}


def subparsers() -> dict[str, argparse.ArgumentParser]:
    parser = cli.build_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return action.choices


def test_every_command_declares_a_guard_and_a_step():
    for name, p in subparsers().items():
        defaults = p._defaults
        assert defaults["guard"] is (require_root if name in ROOT_COMMANDS else require_user), name
        assert callable(defaults["step"]), name


def test_main_runs_guard_before_step(monkeypatch):
    order = []
    monkeypatch.setattr(cli.manifest, "load", lambda path: {})
    monkeypatch.setattr(cli.Config, "from_manifest", classmethod(lambda cls, d: "cfg"))
    monkeypatch.setattr(cli, "cleanup", lambda data: order.append(("cleanup", data)))
    parser = cli.build_parser()
    monkeypatch.setattr(cli, "build_parser", lambda: parser)
    for p in subparsers().values():
        p.set_defaults(guard=lambda: order.append("guard"))

    cli.main(["cleanup"])

    assert order == ["guard", ("cleanup", {})]
