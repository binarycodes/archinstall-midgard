from typer.testing import CliRunner

from installer import cli
from installer.shell import require_root, require_user

ROOT_COMMANDS = {"install", "post-chroot", "boot-entries"}


def test_every_command_declares_a_guard():
    for c in cli.app.registered_commands:
        expected = require_root if c.name in ROOT_COMMANDS else require_user
        assert c.callback.guard is expected, c.name


def test_command_runs_guard_before_step(monkeypatch):
    order = []
    monkeypatch.setattr(cli.manifest, "load", lambda path: {})
    monkeypatch.setattr(cli.Config, "from_manifest", classmethod(lambda cls, d: "cfg"))
    monkeypatch.setattr(cli, "cleanup", lambda data: order.append(("cleanup", data)))
    monkeypatch.setattr(cli.cleanup_cmd, "guard", lambda: order.append("guard"))

    result = CliRunner().invoke(cli.app, ["cleanup"])

    assert result.exit_code == 0, result.output
    assert order == ["guard", ("cleanup", {})]


def test_h_is_short_for_help():
    for args in (["-h"], ["cleanup", "-h"]):
        result = CliRunner().invoke(cli.app, args)
        assert result.exit_code == 0, args
        assert "Usage:" in result.output, args


def test_annotate_takes_an_optional_manifest_path(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cli, "annotate", seen.append)
    monkeypatch.setattr(cli.annotate_cmd, "guard", lambda: None)

    CliRunner().invoke(cli.app, ["annotate"])
    CliRunner().invoke(cli.app, ["annotate", str(tmp_path / "m.yml")])

    assert seen == [cli.paths.MANIFEST, tmp_path / "m.yml"]
