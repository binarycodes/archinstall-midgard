import pytest
from typer.testing import CliRunner

from installer import cli
from installer.shell import require_root, require_user

ROOT_COMMANDS = {"install", "post-chroot", "boot-entries"}
ANY_USER_COMMANDS = {"check", "validate"}


def test_every_command_declares_a_guard():
    for c in cli.app.registered_commands:
        if c.name in ANY_USER_COMMANDS:
            expected = cli.allow_any
        elif c.name in ROOT_COMMANDS:
            expected = require_root
        else:
            expected = require_user
        assert c.callback.guard is expected, c.name


def test_command_runs_guard_before_step(monkeypatch):
    order = []
    monkeypatch.setattr(cli.manifest, "load", lambda path: {})
    monkeypatch.setattr(cli, "validate", lambda data: [])
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
    monkeypatch.setattr(cli, "load_manifest", lambda path: {})
    monkeypatch.setattr(cli.annotate_cmd, "guard", lambda: None)

    CliRunner().invoke(cli.app, ["annotate"])
    CliRunner().invoke(cli.app, ["annotate", str(tmp_path / "m.yml")])

    assert seen == [cli.paths.MANIFEST, tmp_path / "m.yml"]


def test_check_u_prints_detected_ucode(monkeypatch):
    monkeypatch.setattr(cli.cpu, "ucode", lambda: "amd-ucode")
    result = CliRunner().invoke(cli.app, ["check", "-u"])
    assert result.exit_code == 0, result.output
    assert result.output == "amd-ucode\n"


def test_check_u_reports_no_ucode(monkeypatch):
    monkeypatch.setattr(cli.cpu, "ucode", lambda: None)
    result = CliRunner().invoke(cli.app, ["check", "--ucode"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("none")


def test_check_without_options_fails():
    result = CliRunner().invoke(cli.app, ["check"])
    assert result.exit_code != 0


def test_check_r_prints_ram(monkeypatch):
    monkeypatch.setattr(cli.memory, "total_gib", lambda: 31.06)
    result = CliRunner().invoke(cli.app, ["check", "-r"])
    assert result.exit_code == 0, result.output
    assert result.output == "31.1 GiB\n"


def test_check_prints_each_requested_check_in_order(monkeypatch):
    monkeypatch.setattr(cli.cpu, "ucode", lambda: "intel-ucode")
    monkeypatch.setattr(cli.memory, "total_gib", lambda: 16.0)
    result = CliRunner().invoke(cli.app, ["check", "-r", "-u"])
    assert result.output == "intel-ucode\n16.0 GiB\n"


def test_check_s_prints_swap_size(monkeypatch):
    monkeypatch.setattr(cli.memory, "total_gib", lambda: 31.06)
    result = CliRunner().invoke(cli.app, ["check", "-s"])
    assert result.exit_code == 0, result.output
    assert result.output == "33 GiB\n"


def write_manifest(tmp_path, text: str):
    path = tmp_path / "m.yml"
    path.write_text(text)
    return path


def test_validate_ok_for_repo_manifest(monkeypatch):
    monkeypatch.setattr(cli, "skipped_checks", list)
    result = CliRunner().invoke(cli.app, ["validate"])
    assert result.exit_code == 0, result.output
    assert result.output == f"{cli.paths.MANIFEST}: ok\n"


def test_validate_lists_every_problem(tmp_path):
    path = write_manifest(tmp_path, "username: u\nbogus: 1\n")
    result = CliRunner().invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 1
    assert "bogus: unknown key" in result.output
    assert "timezone: missing" in result.output


def test_validate_reports_load_errors(tmp_path):
    path = write_manifest(tmp_path, "username: a\nusername: b\n")
    result = CliRunner().invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 1
    assert "duplicate key 'username'" in result.output


def test_validate_packages_runs_lookups(monkeypatch):
    monkeypatch.setattr(cli, "skipped_checks", list)
    monkeypatch.setattr(cli, "check_repo_packages", lambda data: ["packages: 'x' not found"])
    monkeypatch.setattr(cli, "check_aur_packages", lambda data: [])
    plain = CliRunner().invoke(cli.app, ["validate"])
    checked = CliRunner().invoke(cli.app, ["validate", "-p"])
    assert plain.exit_code == 0
    assert checked.exit_code == 1
    assert "packages: 'x' not found" in checked.output


def test_steps_stop_on_an_invalid_manifest(monkeypatch, tmp_path):
    path = write_manifest(tmp_path, "username: u\n")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    monkeypatch.setattr(cli.cleanup_cmd, "guard", lambda: None)
    monkeypatch.setattr(cli, "cleanup", lambda data: pytest.fail("ran on an invalid manifest"))
    result = CliRunner().invoke(cli.app, ["cleanup"])
    assert result.exit_code == 1
    assert "timezone: missing" in result.output


def test_check_d_is_a_dry_run(monkeypatch):
    from installer import disk

    calls = []
    target = disk.Disk("sda", "/dev/sda", 500 * 1024**3, "Disk", "SN", "sata")
    monkeypatch.setattr(cli.memory, "total_gib", lambda: 16.0)
    monkeypatch.setattr(disk, "candidates", lambda: [target])
    monkeypatch.setattr(disk, "output", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr("installer.shell.subprocess.run", lambda *a, **k: calls.append(a))
    result = CliRunner().invoke(cli.app, ["check", "-d"], input="1\nsda\n")
    assert result.exit_code == 0, result.output
    assert "Dry run: install would erase /dev/sda as shown above." in result.output
    assert "/dev/sda2" in result.output
    assert calls == []


def test_check_d_reports_abort(monkeypatch):
    from installer import disk

    target = disk.Disk("sda", "/dev/sda", 500 * 1024**3, "Disk", "SN", "sata")
    monkeypatch.setattr(cli.memory, "total_gib", lambda: 16.0)
    monkeypatch.setattr(disk, "candidates", lambda: [target])
    result = CliRunner().invoke(cli.app, ["check", "--disk"], input="1\nno\n")
    assert result.exit_code == 1
    assert "Disk selection aborted: not confirmed" in result.output


@pytest.mark.parametrize("step", ["install", "post-chroot"])
def test_hostname_is_required(monkeypatch, step):
    monkeypatch.setattr(cli, "install", lambda *a: pytest.fail("ran"))
    monkeypatch.setattr(cli, "post_chroot", lambda *a: pytest.fail("ran"))
    result = CliRunner().invoke(cli.app, [step])
    assert result.exit_code == 2
    assert "--hostname" in result.output


def test_install_passes_hostname(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.install_cmd, "guard", lambda: None)
    monkeypatch.setattr(cli, "install", lambda cfg, data, name: seen.append(name))
    result = CliRunner().invoke(cli.app, ["install", "--hostname", "midgard"])
    assert result.exit_code == 0, result.output
    assert seen == ["midgard"]


def test_post_chroot_rejects_invalid_hostname(monkeypatch):
    monkeypatch.setattr(cli.post_chroot_cmd, "guard", lambda: None)
    monkeypatch.setattr(cli, "post_chroot", lambda *a: pytest.fail("ran"))
    result = CliRunner().invoke(cli.app, ["post-chroot", "--hostname", "Bad_Name"])
    assert result.exit_code == 2
    assert "is not valid" in result.output
