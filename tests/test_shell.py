import pytest

from installer import shell


@pytest.fixture
def ran(monkeypatch):
    calls = []
    monkeypatch.setattr(shell.subprocess, "run", lambda args, **kwargs: calls.append(args))
    return calls


def test_run_is_silent_by_default(ran, monkeypatch, capsys):
    monkeypatch.setattr(shell, "verbose", False)
    shell.run("echo", "hi there")
    assert ran == [("echo", "hi there")]
    assert capsys.readouterr().err == ""


def test_run_echoes_the_command_when_verbose(ran, monkeypatch, capsys):
    monkeypatch.setattr(shell, "verbose", True)
    shell.run("echo", "hi there")
    assert capsys.readouterr().err == "+ echo 'hi there'\n"


def test_quiet_run_stays_silent_when_verbose(ran, monkeypatch, capsys):
    monkeypatch.setattr(shell, "verbose", True)
    shell.run("lsblk", quiet=True)
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(("verbose", "expected"), [(False, ""), (True, "+ write {}\n")])
def test_write_file_echoes_only_when_verbose(tmp_path, monkeypatch, capsys, verbose, expected):
    monkeypatch.setattr(shell, "verbose", verbose)
    path = tmp_path / "f"
    shell.write_file(path, "x")
    assert path.read_text() == "x"
    assert capsys.readouterr().err == expected.format(path)
