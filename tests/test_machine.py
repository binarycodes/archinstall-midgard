import pytest

from installer import machine, manifest
from installer.hardware import FEATURES
from installer.machine import MachineError

BASE = """\
username: u
timezone: UTC
locale: en_US.UTF-8
keymap: us
install_repo: dots
packages: [foot, sway]
gsettings:
  org.gnome.desktop.interface:
    color-scheme: prefer-dark
git_repos: [https://example.com/dots.git]
"""


@pytest.fixture
def repo(tmp_path):
    """Write the base manifest and the given profiles; returns the manifest path."""

    def write(base: str = BASE, **profiles: str):
        (tmp_path / "manifest.yml").write_text(base)
        (tmp_path / "profiles").mkdir(exist_ok=True)
        for name, text in profiles.items():
            (tmp_path / "profiles" / f"{name}.yml").write_text(text)
        return tmp_path / "manifest.yml"

    return write


def problems(path, only=None):
    return machine.check(machine.read(path), only)


def test_empty_profile_merges_to_exactly_the_base(repo):
    path = repo(empty="")
    assert machine.load("empty", path, []).data == manifest.load(path)


def test_profile_chain_is_merged_in_order(repo):
    path = repo(
        a="extends: [b]\nkeymap: fi\npackages: [vim]\n",
        b="keymap: de\npackages: [vim, mpv]\n",
    )
    loaded = machine.load("a", path, [])
    assert loaded.chain == ["b", "a"]
    assert loaded.describe() == "a (base → b → a)"
    assert loaded.cfg.keymap == "fi"
    assert loaded.data["packages"] == ["foot", "sway", "vim", "mpv"]


def test_extends_is_not_part_of_the_merged_manifest(repo):
    path = repo(a="extends: b\n", b="")
    assert "extends" not in machine.load("a", path, []).data


def test_unknown_profile(repo):
    path = repo(a="", b="")
    with pytest.raises(MachineError) as e:
        machine.load("x", path, [])
    assert e.value.problems == ["unknown profile 'x'; profiles in profiles/: a, b"]


def test_without_profiles_only_the_base_is_checked(repo):
    assert problems(repo()) == []
    assert problems(repo(BASE + "bogus: 1\n")) == ["manifest.yml: bogus: unknown key"]


def test_profile_file_is_checked_on_its_own(repo):
    path = repo(a="hostname: h\ndisk: /dev/sda\nextends: [x]\n")
    assert problems(path) == [
        "profiles/a.yml: hostname: unknown key",
        "profiles/a.yml: disk: unknown key",
        "profiles/a.yml: extends[0]: unknown profile 'x'; profiles in profiles/: a",
    ]


def test_extends_is_unknown_in_the_base(repo):
    path = repo(BASE + "extends: [a]\n", a="")
    assert problems(path) == ["manifest.yml: extends: unknown key"]


def test_cycles_are_reported(repo):
    path = repo(a="extends: b\n", b="extends: a\n")
    assert problems(path) == [
        "profiles/a.yml: extension cycle: a → b → a",
        "profiles/b.yml: extension cycle: b → a → b",
    ]


def test_base_must_be_complete_on_its_own(repo):
    base = BASE.replace("keymap: us\n", "").replace("dots.git", "other.git")
    path = repo(base, a="keymap: fi\n")
    assert problems(path, "a") == [
        "manifest.yml: keymap: missing",
        "manifest.yml: git_repos: must include the install_repo 'dots'",
    ]


def test_profile_overrides_the_base(repo):
    path = repo(a="keymap: fi\ninstall_repo: other\ngit_repos: [https://example.com/other.git]\n")
    data = machine.load("a", path, []).data
    assert (data["keymap"], data["install_repo"]) == ("fi", "other")


def test_missing_keys_after_merge(repo, monkeypatch):
    # the merge never drops a key, so only the merged check would catch one going missing
    path = repo(a="")
    monkeypatch.setattr(machine, "merged", lambda files, chain, features: {"username": "u"})
    assert "a (base → features → a): timezone: missing" in problems(path)


def test_merged_result_is_checked_across_files(repo):
    path = repo(a="post_chroot: [foot]\n")
    assert problems(path) == [
        "a (base → features → a): packages[0]: 'foot' is already listed at post_chroot[0]"
    ]


def test_only_checks_the_profile_and_what_it_extends(repo):
    path = repo(a="extends: b\n", b="", broken="bogus: 1\n", bad_yaml="a: [\n")
    assert problems(path, "a") == []
    assert problems(path, "broken") == ["profiles/broken.yml: bogus: unknown key"]
    assert problems(path, "bad_yaml")[0].startswith("profiles/bad_yaml.yml: line 2: invalid YAML")


def test_chain_without_validating(repo):
    path = repo(BASE + "bogus: 1\n", a="extends: [b]\n", b="")
    assert machine.chain("a", path) == ["b", "a"]


def test_chain_errors(repo):
    path = repo(a="extends: b\n", b="extends: a\n")
    with pytest.raises(MachineError) as e:
        machine.chain("a", path)
    assert e.value.problems == ["extension cycle: a → b → a"]


def test_saved_profile_round_trip(repo, tmp_path, monkeypatch):
    path = repo(gaming="keymap: fi\n", workstation="")
    monkeypatch.setattr(machine.profiles, "write_file", lambda p, text: p.write_text(text))
    machine.profiles.save("gaming", str(tmp_path / "mnt"))
    saved = tmp_path / "mnt" / "etc" / "installer" / "profile"
    loaded = machine.load_saved(path, saved, [])
    assert loaded.profile == "gaming"
    assert loaded.cfg.keymap == "fi"


def test_missing_saved_profile(repo, tmp_path):
    path = repo(a="", b="")
    with pytest.raises(MachineError) as e:
        machine.load_saved(path, tmp_path / "missing", [])
    listing = "profiles in profiles/: a, b"
    assert e.value.problems == [
        f"{tmp_path / 'missing'}: cannot read: No such file or directory; {listing}"
    ]


def test_unknown_saved_profile(repo, tmp_path):
    path = repo(a="")
    saved = tmp_path / "saved"
    saved.write_text("gone\n")
    with pytest.raises(MachineError) as e:
        machine.load_saved(path, saved, [])
    assert e.value.problems == [f"{saved}: unknown profile 'gone'; profiles in profiles/: a"]


@pytest.fixture
def features(tmp_path):
    def write(**files: str):
        (tmp_path / "features").mkdir(exist_ok=True)
        for name, text in files.items():
            (tmp_path / "features" / f"{name}.yml").write_text(text)

    return write


def test_merge_order_is_base_then_features_then_profile(repo, features):
    path = repo(a="gsettings:\n  org.gnome.desktop.interface:\n    color-scheme: x\n")
    features(
        wifi="packages: [iwd]\ngsettings:\n  org.gnome.desktop.interface:\n    color-scheme: w\n",
        battery="packages: [tlp]\ngsettings:\n  org.gnome.desktop.interface:\n    font: b\n",
    )
    data = machine.load("a", path, ["battery", "wifi"]).data
    # battery comes before wifi in the fixed order, whatever order they were passed in
    assert data["packages"] == ["foot", "sway", "tlp", "iwd"]
    assert data["gsettings"]["org.gnome.desktop.interface"] == {
        "color-scheme": "x",
        "font": "b",
    }
    assert machine.load("a", path, ["wifi", "battery"]).data == data


def test_only_detected_features_are_merged(repo, features):
    path = repo(a="")
    features(wifi="packages: [iwd]\n", bluetooth="packages: [bluez]\n")
    assert machine.load("a", path, ["wifi"]).data["packages"] == ["foot", "sway", "iwd"]
    assert machine.load("a", path, []).data == manifest.load(path)


def test_detected_feature_without_a_file_adds_nothing(repo, features):
    path = repo(a="")
    features(wifi="packages: [iwd]\n")
    assert machine.load("a", path, ["lid", "touchpad"]).data == manifest.load(path)


def test_feature_file_problems(repo, features):
    path = repo(a="")
    features(wfi="", wifi="extends: [a]\nhostname: h\npackages: [Bad]\n", lid="a: [\n")
    found = problems(path, "a")
    assert found[0].startswith("features/lid.yml: line 2: invalid YAML")
    assert found[1:] == [
        f"features/wfi.yml: unknown feature 'wfi'; known features: {', '.join(FEATURES)}",
        "features/wifi.yml: extends: unknown key",
        "features/wifi.yml: hostname: unknown key",
        "features/wifi.yml: packages[0]: 'Bad' is not a valid package name",
    ]


def test_merged_result_is_checked_with_every_feature(repo, features):
    path = repo(a="aur_packages: [iwd]\n")
    features(wifi="post_chroot: [iwd]\n")
    assert problems(path) == [
        "a (base → features → a): aur_packages[0]: 'iwd' is already listed at post_chroot[0]"
    ]


@pytest.mark.parametrize("detected", [[], ["wifi"], ["bluetooth"], ["wifi", "bluetooth"]])
def test_repo_services_and_managed_packages_follow_features(detected):
    from installer import paths

    data = machine.load("workstation", paths.MANIFEST, detected).data
    services = data["system_services"]
    managed = manifest.managed_packages(data)
    wifi, bluetooth = "wifi" in detected, "bluetooth" in detected
    assert ("iwd" in services, "iwd" in manifest.section(data, "post_chroot")) == (wifi, wifi)
    assert ("iwd" in managed) is wifi
    assert ("bluetooth" in services) is bluetooth
    assert ("bluez" in managed, "bluez-utils" in managed) == (bluetooth, bluetooth)
