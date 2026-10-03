import pytest

from installer import install
from installer.config import Config
from installer.disk import DiskError
from installer.machine import Machine

URL = "https://github.com/me/install.git"
SHA = "0611c08aa0d6a0e9a8bd31c0e5e7c4b8f2d7e3a1"

MACHINE = Machine(
    "gaming", ["gaming"], ["wifi"], Config("u", "UTC", "en_US.UTF-8", "us", "repo"), {}
)


@pytest.fixture
def ready(monkeypatch, tmp_path):
    monkeypatch.setattr(install, "EFI_VARS", tmp_path)
    monkeypatch.setattr(install, "network_reachable", lambda: True)
    monkeypatch.setattr(install.metadata, "git_source", lambda repo: ("url", "sha"))


@pytest.fixture
def loads(monkeypatch):
    monkeypatch.setattr(install, "preflight", lambda hostname, profile: [])
    monkeypatch.setattr(install.machine, "load", lambda profile, path, features: MACHINE)
    monkeypatch.setattr(install.hardware, "detect_features", lambda: ["wifi"])
    monkeypatch.setattr(install.metadata, "git_source", lambda repo: (URL, SHA))
    monkeypatch.setattr(install.metadata, "now", lambda: "2026-10-03T12:00:00Z")
    monkeypatch.setattr(install.memory, "total_gib", lambda: 16.0)


def test_preflight_passes(ready):
    assert install.preflight("midgard", "workstation") == []


def test_preflight_needs_uefi(ready, monkeypatch, tmp_path):
    monkeypatch.setattr(install, "EFI_VARS", tmp_path / "missing")
    assert install.preflight("midgard", "workstation") == [
        "not booted in UEFI mode; boot entries are created with EFISTUB"
    ]


def test_preflight_needs_network(ready, monkeypatch):
    monkeypatch.setattr(install, "network_reachable", lambda: False)
    assert install.preflight("midgard", "workstation") == [
        "no network: cannot reach archlinux.org:443, which pacstrap needs"
    ]


def test_network_reachable_handles_errors(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("unreachable")

    monkeypatch.setattr(install.socket, "create_connection", refuse)
    assert not install.network_reachable()


def test_install_stops_before_disk_selection_when_preflight_fails(monkeypatch, capsys):
    monkeypatch.setattr(install, "preflight", lambda hostname, profile: ["no network"])
    monkeypatch.setattr(install, "select_disk", lambda swap: pytest.fail("disk offered"))
    with pytest.raises(SystemExit) as exit:
        install.install("midgard", "gaming")
    assert exit.value.code == 1
    assert capsys.readouterr().err == "Cannot install:\n  no network\n"


def test_install_stops_when_disk_selection_aborts(loads, monkeypatch, capsys):
    def abort(swap):
        raise DiskError("not confirmed")

    monkeypatch.setattr(install, "select_disk", abort)
    monkeypatch.setattr(install, "create_partitions", lambda *a: pytest.fail("partitioned"))
    with pytest.raises(SystemExit) as exit:
        install.install("midgard", "gaming")
    assert exit.value.code == 1
    assert capsys.readouterr().err == "\nInstall aborted: not confirmed\n"


def test_install_partitions_the_selected_disk(loads, monkeypatch):
    seen = []
    monkeypatch.setattr(install, "select_disk", lambda swap: ("disk", swap))
    monkeypatch.setattr(install, "create_partitions", lambda *args: seen.append(args))

    class Stop(Exception):
        pass

    def stop(*args):
        raise Stop

    monkeypatch.setattr(install, "pacstrap", stop)
    with pytest.raises(Stop):
        install.install("midgard", "gaming")
    assert seen == [(("disk", 17), 17)]


def test_preflight_checks_hostname(ready):
    [problem] = install.preflight("Midgard", "workstation")
    assert problem.startswith("hostname 'Midgard' is not valid")


@pytest.fixture
def steps(loads, monkeypatch):
    """Every step install takes, in order, with nothing actually run."""
    seen = []
    monkeypatch.setattr(install, "select_disk", lambda swap: "disk")
    monkeypatch.setattr(install, "create_partitions", lambda *args: seen.append("partitions"))
    monkeypatch.setattr(install, "pacstrap", lambda *args: seen.append("pacstrap"))
    monkeypatch.setattr(install.metadata, "write", lambda data, root: seen.append(("save", data)))
    monkeypatch.setattr(install, "run", lambda *args, **kwargs: seen.append(args))
    return seen


def test_install_shows_hostname_and_passes_it_to_post_chroot(steps, capsys):
    install.install("midgard", "gaming")
    assert "Installing as midgard" in capsys.readouterr().out
    post_chroot = next(s for s in steps if "post-chroot" in s)
    assert post_chroot[-3:] == ("post-chroot", "--hostname", "midgard")


def test_preflight_checks_the_profile(ready, monkeypatch, tmp_path):
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "a.yml").write_text("")
    monkeypatch.setattr(install.paths, "MANIFEST", tmp_path / "manifest.yml")
    (tmp_path / "manifest.yml").write_text("username: u\n")
    assert install.preflight("midgard", "b") == ["unknown profile 'b'; profiles in profiles/: a"]
    assert "manifest.yml: timezone: missing" in install.preflight("midgard", "a")


def test_install_shows_the_profile_chain(steps, monkeypatch, capsys):
    chained = Machine("a", ["b", "a"], ["battery", "wifi"], MACHINE.cfg, {})
    monkeypatch.setattr(install.machine, "load", lambda profile, path, features: chained)
    install.install("midgard", "a")
    out = capsys.readouterr().out
    assert "Installing as midgard with profile a (base → b → a)\n" in out
    assert "Detected features: battery, wifi\n" in out


def test_install_merges_the_detected_features(steps, monkeypatch):
    seen = []
    monkeypatch.setattr(
        install.machine, "load", lambda profile, path, features: seen.append(features) or MACHINE
    )
    install.install("midgard", "gaming")
    assert seen == [["wifi"]]


def test_install_records_metadata_after_pacstrap_before_the_chroot(steps):
    install.install("midgard", "gaming")
    saved = install.metadata.Metadata("gaming", ["wifi"], URL, SHA, "2026-10-03T12:00:00Z")
    first_chroot = next(i for i, s in enumerate(steps) if s[0] == "arch-chroot")
    assert steps.index("pacstrap") + 1 == steps.index(("save", saved))
    assert steps.index(("save", saved)) < first_chroot


def test_preflight_needs_the_git_source(ready, monkeypatch):
    def fail(repo):
        raise install.metadata.MetadataError("cannot read the git origin and commit of /r: boom")

    monkeypatch.setattr(install.metadata, "git_source", fail)
    assert install.preflight("midgard", "workstation") == [
        "cannot read the git origin and commit of /r: boom"
    ]
