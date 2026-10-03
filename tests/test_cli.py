import pytest
from typer.testing import CliRunner

from installer import cli
from installer.machine import Files, Machine
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
    loaded = Machine("p", ["p"], "cfg", {})
    monkeypatch.setattr(cli.machine, "load_saved", lambda path, saved: loaded)
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
    monkeypatch.setattr(cli, "check_files", lambda path: Files("m", {}, None, {}, {}, []))
    monkeypatch.setattr(cli.annotate_cmd, "guard", lambda: None)

    CliRunner().invoke(cli.app, ["annotate"])
    CliRunner().invoke(cli.app, ["annotate", str(tmp_path / "m.yml")])

    assert seen == [[cli.paths.MANIFEST], [tmp_path / "m.yml"]]


def test_annotate_includes_every_profile(monkeypatch, tmp_path):
    seen = []
    path = write_manifest(tmp_path, VALID, b="", a="")
    monkeypatch.setattr(cli, "annotate", seen.append)
    monkeypatch.setattr(cli.annotate_cmd, "guard", lambda: None)
    result = CliRunner().invoke(cli.app, ["annotate", str(path)])
    assert result.exit_code == 0, result.output
    assert seen == [[path, tmp_path / "profiles" / "a.yml", tmp_path / "profiles" / "b.yml"]]


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


VALID = """\
username: u
timezone: UTC
locale: en_US.UTF-8
keymap: us
install_repo: dots
git_repos: [https://example.com/dots.git]
"""


def write_manifest(tmp_path, text: str, **profiles: str):
    """m.yml with text, and profiles/<name>.yml for each keyword; one empty profile if none."""
    path = tmp_path / "m.yml"
    path.write_text(text)
    (tmp_path / "profiles").mkdir()
    for name, profile in (profiles or {"p": ""}).items():
        (tmp_path / "profiles" / f"{name}.yml").write_text(profile)
    return path


def test_validate_ok_for_repo_manifest(monkeypatch):
    monkeypatch.setattr(cli, "skipped_checks", list)
    result = CliRunner().invoke(cli.app, ["validate"])
    assert result.exit_code == 0, result.output
    assert result.output == (
        "manifest.yml: ok\ngaming (base → gaming): ok\nworkstation (base → workstation): ok\n"
    )


def test_validate_lists_every_problem(tmp_path):
    path = write_manifest(tmp_path, VALID + "bogus: 1\n", p="disk: x\nmore: 1\n")
    result = CliRunner().invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 1
    assert result.output == (
        "3 problem(s):\n"
        "  m.yml: bogus: unknown key\n"
        "  profiles/p.yml: disk: unknown key\n"
        "  profiles/p.yml: more: unknown key\n"
    )


def test_validate_needs_a_complete_base(tmp_path):
    path = write_manifest(tmp_path, "username: u\n", p="timezone: UTC\n")
    result = CliRunner().invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 1
    assert "  m.yml: timezone: missing\n" in result.output


def test_validate_checks_the_merged_result(tmp_path):
    path = write_manifest(tmp_path, VALID + "packages: [foot]\n", p="post_chroot: [foot]\n")
    result = CliRunner().invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 1
    assert "  p (base → p): packages[0]: 'foot' is already listed at post_chroot[0]\n" in (
        result.output
    )


def test_validate_reports_load_errors(tmp_path):
    path = write_manifest(tmp_path, "username: a\nusername: b\n")
    result = CliRunner().invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 1
    assert "m.yml: line 2: duplicate key 'username'" in result.output


def test_validate_profile_checks_just_that_one(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "skipped_checks", list)
    path = write_manifest(tmp_path, VALID, a="extends: b\n", b="", c="bogus: 1\n")
    result = CliRunner().invoke(cli.app, ["validate", str(path), "--profile", "a"])
    assert result.exit_code == 0, result.output
    assert result.output == "m.yml: ok\na (base → b → a): ok\n"


def test_validate_unknown_profile(tmp_path):
    path = write_manifest(tmp_path, VALID, a="", b="")
    result = CliRunner().invoke(cli.app, ["validate", str(path), "--profile", "x"])
    assert result.exit_code == 1
    assert "unknown profile 'x'; profiles in profiles/: a, b" in result.output


def test_validate_packages_runs_lookups(monkeypatch):
    monkeypatch.setattr(cli, "skipped_checks", list)
    monkeypatch.setattr(cli, "check_repo_packages", lambda data: ["packages: 'x' not found"])
    monkeypatch.setattr(cli, "check_aur_packages", lambda data: [])
    plain = CliRunner().invoke(cli.app, ["validate"])
    checked = CliRunner().invoke(cli.app, ["validate", "-p"])
    assert plain.exit_code == 0
    assert checked.exit_code == 1
    assert "packages: 'x' not found" in checked.output


@pytest.fixture
def saved(monkeypatch, tmp_path):
    """The saved profile file; cleanup runs with its guard off and records its data."""
    path = tmp_path / "saved"
    monkeypatch.setattr(cli, "SAVED_PROFILE", path)
    monkeypatch.setattr(cli.cleanup_cmd, "guard", lambda: None)
    return path


def test_steps_stop_on_an_invalid_manifest(monkeypatch, tmp_path, saved):
    path = write_manifest(tmp_path, "username: u\n")
    saved.write_text("p\n")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    monkeypatch.setattr(cli, "cleanup", lambda data: pytest.fail("ran on an invalid manifest"))
    result = CliRunner().invoke(cli.app, ["cleanup"])
    assert result.exit_code == 1
    assert "m.yml: timezone: missing" in result.output


def test_steps_use_the_saved_profile(monkeypatch, tmp_path, saved):
    seen = []
    path = write_manifest(tmp_path, VALID, a="keymap: fi\n", b="")
    saved.write_text("a\n")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    monkeypatch.setattr(cli, "cleanup", seen.append)
    result = CliRunner().invoke(cli.app, ["cleanup"])
    assert result.exit_code == 0, result.output
    assert [data["keymap"] for data in seen] == ["fi"]


def test_steps_stop_without_a_saved_profile(monkeypatch, tmp_path, saved):
    path = write_manifest(tmp_path, VALID, a="", b="")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    monkeypatch.setattr(cli, "cleanup", lambda data: pytest.fail("ran without a profile"))
    result = CliRunner().invoke(cli.app, ["cleanup"])
    assert result.exit_code == 1
    assert f"{saved}: cannot read: No such file or directory; profiles in profiles/: a, b" in (
        result.output
    )


def test_steps_stop_on_an_unknown_saved_profile(monkeypatch, tmp_path, saved):
    path = write_manifest(tmp_path, VALID, a="")
    saved.write_text("gone\n")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    monkeypatch.setattr(cli, "cleanup", lambda data: pytest.fail("ran on an unknown profile"))
    result = CliRunner().invoke(cli.app, ["cleanup"])
    assert result.exit_code == 1
    assert f"{saved}: unknown profile 'gone'; profiles in profiles/: a" in result.output


@pytest.mark.parametrize("step", ["packages", "daily", "cleanup", "customize", "boot-entries"])
def test_steps_take_no_profile_option(step):
    result = CliRunner().invoke(cli.app, [step, "--profile", "a"])
    assert result.exit_code == 2
    assert "No such option" in result.output


def test_check_c_prints_the_chain(monkeypatch, tmp_path):
    path = write_manifest(tmp_path, VALID, a="extends: [c, b]\n", b="extends: c\n", c="")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    result = CliRunner().invoke(cli.app, ["check", "-c", "a"])
    assert result.exit_code == 0, result.output
    assert result.output == "base → c → b → a\n"


def test_check_c_never_reads_the_saved_profile(monkeypatch, tmp_path):
    path = write_manifest(tmp_path, VALID, a="")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    monkeypatch.setattr(cli.machine, "load_saved", lambda *a: pytest.fail("read saved profile"))
    result = CliRunner().invoke(cli.app, ["check", "--chain", "a"])
    assert result.output == "base → a\n"


def test_check_c_unknown_profile(monkeypatch, tmp_path):
    path = write_manifest(tmp_path, VALID, a="", b="")
    monkeypatch.setattr(cli.paths, "MANIFEST", path)
    result = CliRunner().invoke(cli.app, ["check", "-c", "x"])
    assert result.exit_code == 1
    assert "unknown profile 'x'; profiles in profiles/: a, b" in result.output


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


@pytest.mark.parametrize(
    ("args", "missing"),
    [
        (["install", "--profile", "gaming"], "--hostname"),
        (["post-chroot"], "--hostname"),
        (["install", "--hostname", "midgard"], "--profile"),
    ],
)
def test_hostname_and_profile_are_required(monkeypatch, args, missing):
    monkeypatch.setattr(cli, "install", lambda *a: pytest.fail("ran"))
    monkeypatch.setattr(cli, "post_chroot", lambda *a: pytest.fail("ran"))
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 2
    assert f"Missing option '{missing}'" in result.output


def test_install_passes_hostname_and_profile(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.install_cmd, "guard", lambda: None)
    monkeypatch.setattr(cli, "install", lambda *args: seen.append(args))
    result = CliRunner().invoke(
        cli.app, ["install", "--hostname", "midgard", "--profile", "gaming"]
    )
    assert result.exit_code == 0, result.output
    assert seen == [("midgard", "gaming")]


def test_post_chroot_rejects_invalid_hostname(monkeypatch):
    monkeypatch.setattr(cli.post_chroot_cmd, "guard", lambda: None)
    monkeypatch.setattr(cli, "post_chroot", lambda *a: pytest.fail("ran"))
    result = CliRunner().invoke(cli.app, ["post-chroot", "--hostname", "Bad_Name"])
    assert result.exit_code == 2
    assert "is not valid" in result.output
