import subprocess

import pytest

from installer import install
from installer.config import Config
from installer.machine import Machine
from installer.user_inputs import InputError, UserInputs

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
    monkeypatch.setattr(install.hardware, "detect_features", list)
    monkeypatch.setattr(install, "check_repo_packages", lambda data: [])
    monkeypatch.setattr(install, "check_aur_packages", lambda data: [])
    monkeypatch.setattr(install, "unreachable_repos", lambda data: [])


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
    monkeypatch.setattr(install, "collect", lambda *a: pytest.fail("input asked"))
    with pytest.raises(SystemExit) as exit:
        install.install("midgard", "gaming")
    assert exit.value.code == 1
    assert capsys.readouterr().err == "Cannot install:\n  no network\n"


def test_install_stops_when_input_is_aborted(loads, monkeypatch, capsys):
    def abort(swap, username):
        raise InputError("not confirmed")

    monkeypatch.setattr(install, "collect", abort)
    monkeypatch.setattr(install, "create_partitions", lambda *a: pytest.fail("partitioned"))
    with pytest.raises(SystemExit) as exit:
        install.install("midgard", "gaming")
    assert exit.value.code == 1
    assert capsys.readouterr().err == "\nInstall aborted: not confirmed\n"


def test_install_partitions_the_selected_disk(loads, monkeypatch):
    seen = []
    monkeypatch.setattr(install, "collect", lambda swap, user: UserInputs(("disk", swap), {}))
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
    passwords = {"root": "r00t", "u": "s3cret"}

    def collect(swap, username):
        seen.append(("inputs", username))
        return UserInputs("disk", passwords)

    monkeypatch.setattr(install, "collect", collect)
    monkeypatch.setattr(install, "create_partitions", lambda *args: seen.append("partitions"))
    monkeypatch.setattr(install, "pacstrap", lambda *args: seen.append("pacstrap"))
    monkeypatch.setattr(install.metadata, "write", lambda data, root: seen.append(("save", data)))
    monkeypatch.setattr(install, "run", lambda *args, **kwargs: seen.append((*args, kwargs)))
    return seen


def test_install_collects_every_input_before_changing_anything(steps):
    install.install("midgard", "gaming")
    assert steps.index(("inputs", "u")) + 1 == steps.index("partitions")


def test_install_sets_the_passwords_after_post_chroot_through_stdin(steps):
    install.install("midgard", "gaming")
    post_chroot = next(i for i, s in enumerate(steps) if "post-chroot" in s)
    chpasswd = steps[post_chroot + 1]
    assert chpasswd[:3] == ("arch-chroot", "/mnt", "chpasswd")
    assert chpasswd[3]["input"] == "root:r00t\nu:s3cret\n"
    assert not any("s3cret" in str(arg) for step in steps for arg in step[:-1])


def test_chroot_steps_never_wait_for_git(steps):
    install.install("midgard", "gaming")
    chroot_steps = [s for s in steps if s[0] == "arch-chroot" and "installer" in s]
    assert chroot_steps
    for step in chroot_steps:
        assert step[-1]["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert step[-1]["env"]["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"


def test_user_chroot_steps_drop_roots_session(steps, monkeypatch):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/0/bus")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/0")
    install.install("midgard", "gaming")
    chroot_steps = [s for s in steps if s[0] == "arch-chroot" and "installer" in s]
    for step in chroot_steps:
        as_user = "runuser" in step
        for name in install.ROOT_SESSION:
            assert (name in step[-1]["env"]) is not as_user


def test_install_points_resolv_conf_at_resolved_after_the_last_chroot_step(steps):
    install.install("midgard", "gaming")
    link = ("ln", "-sf", "../run/systemd/resolve/stub-resolv.conf", "/mnt/etc/resolv.conf", {})
    last_chroot = max(i for i, s in enumerate(steps) if s[0] == "arch-chroot")
    assert steps.index(link) > last_chroot


def test_preflight_checks_packages_and_repos(ready, monkeypatch):
    monkeypatch.setattr(install, "check_repo_packages", lambda data: ["packages: 'x' missing"])
    monkeypatch.setattr(install, "check_aur_packages", lambda data: ["aur_packages: 'y' missing"])
    monkeypatch.setattr(install, "unreachable_repos", lambda data: ["git_repos: cannot clone z"])
    assert install.preflight("midgard", "workstation") == [
        "packages: 'x' missing",
        "aur_packages: 'y' missing",
        "git_repos: cannot clone z",
    ]


def test_preflight_skips_lookups_when_the_manifest_is_invalid(ready, monkeypatch):
    monkeypatch.setattr(install, "check_repo_packages", lambda data: pytest.fail("looked up"))
    assert install.preflight("midgard", "missing")[0].startswith("unknown profile 'missing'")


def test_unreachable_repos(monkeypatch):
    calls = []

    def run(*args, **kwargs):
        calls.append((args, kwargs["env"]["GIT_TERMINAL_PROMPT"]))
        return subprocess.CompletedProcess(args, 0 if "ok" in args[2] else 128)

    monkeypatch.setattr(install, "run", run)
    data = {"git_repos": ["https://example.com/ok.git", "git@example.com:me/private.git"]}
    assert install.unreachable_repos(data) == [
        "git_repos: cannot clone git@example.com:me/private.git without a prompt"
    ]
    assert [env for _, env in calls] == ["0", "0"]


def test_install_shows_hostname_and_passes_it_to_post_chroot(steps, capsys):
    install.install("midgard", "gaming")
    assert "Installing as midgard" in capsys.readouterr().out
    post_chroot = next(s for s in steps if "post-chroot" in s)
    assert post_chroot[-4:-1] == ("post-chroot", "--hostname", "midgard")


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


def test_install_without_a_profile(steps, monkeypatch, capsys):
    base = Machine(None, [], ["wifi"], MACHINE.cfg, {})
    monkeypatch.setattr(install.machine, "load", lambda profile, path, features: base)
    install.install("midgard", None)
    assert "Installing as midgard from the base manifest\n" in capsys.readouterr().out
    [saved] = [s[1] for s in steps if s[0] == "save"]
    assert saved.profile == ""


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
