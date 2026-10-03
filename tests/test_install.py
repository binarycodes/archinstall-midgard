import pytest

from installer import install
from installer.config import Config
from installer.disk import DiskError


@pytest.fixture
def ready(monkeypatch, tmp_path):
    monkeypatch.setattr(install, "EFI_VARS", tmp_path)
    monkeypatch.setattr(install, "network_reachable", lambda: True)


def test_preflight_passes(ready):
    assert install.preflight() == []


def test_preflight_needs_uefi(ready, monkeypatch, tmp_path):
    monkeypatch.setattr(install, "EFI_VARS", tmp_path / "missing")
    assert install.preflight() == ["not booted in UEFI mode; boot entries are created with EFISTUB"]


def test_preflight_needs_network(ready, monkeypatch):
    monkeypatch.setattr(install, "network_reachable", lambda: False)
    assert install.preflight() == [
        "no network: cannot reach archlinux.org:443, which pacstrap needs"
    ]


def test_network_reachable_handles_errors(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("unreachable")

    monkeypatch.setattr(install.socket, "create_connection", refuse)
    assert not install.network_reachable()


def test_install_stops_before_disk_selection_when_preflight_fails(monkeypatch, capsys):
    monkeypatch.setattr(install, "preflight", lambda: ["no network"])
    monkeypatch.setattr(install, "select_disk", lambda swap: pytest.fail("disk offered"))
    with pytest.raises(SystemExit) as exit:
        install.install(None, {})
    assert exit.value.code == 1
    assert capsys.readouterr().err == "Cannot install:\n  no network\n"


def test_install_stops_when_disk_selection_aborts(monkeypatch, capsys):
    def abort(swap):
        raise DiskError("not confirmed")

    monkeypatch.setattr(install, "preflight", list)
    monkeypatch.setattr(install.memory, "total_gib", lambda: 16.0)
    monkeypatch.setattr(install, "select_disk", abort)
    monkeypatch.setattr(install, "create_partitions", lambda *a: pytest.fail("partitioned"))
    with pytest.raises(SystemExit) as exit:
        install.install(None, {})
    assert exit.value.code == 1
    assert capsys.readouterr().err == "\nInstall aborted: not confirmed\n"


def test_install_partitions_the_selected_disk(monkeypatch):
    seen = []
    monkeypatch.setattr(install, "preflight", list)
    monkeypatch.setattr(install.memory, "total_gib", lambda: 16.0)
    monkeypatch.setattr(install, "select_disk", lambda swap: ("disk", swap))
    monkeypatch.setattr(install, "create_partitions", lambda *args: seen.append(args))

    class Stop(Exception):
        pass

    def stop(*args):
        raise Stop

    monkeypatch.setattr(install, "pacstrap", stop)
    cfg = Config("u", "h", "UTC", "en_US.UTF-8", "us", "repo")
    with pytest.raises(Stop):
        install.install(cfg, {})
    assert seen == [(("disk", 17), 17)]
