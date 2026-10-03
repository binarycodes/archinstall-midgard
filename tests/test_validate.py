import copy

import pytest

from installer import manifest, paths, validate
from installer.validate import check_aur_packages, supported_locales

VALID = {
    "username": "u",
    "timezone": "Europe/Helsinki",
    "locale": "en_US.UTF-8",
    "keymap": "us",
    "install_repo": "dots",
    "pacstrap": ["base", "git"],
    "post_chroot": ["sudo"],
    "packages": ["foot", "lib32-gcc-libs", "python-pyyaml", "gtk+3", "libc++"],
    "aur_packages": ["yay-bin"],
    "aur_helpers": None,
    "system_services": ["sshd"],
    "user_services": ["pipewire"],
    "url_packages": [{"name": "tool", "url": "https://example.com/tool.pkg.tar.zst"}],
    "pacman_keys": [{"key": "B929081F184DE398E1487552FF8D24F0A3FC59A6", "server": "keys.example"}],
    "gsettings": {"org.gnome.desktop.interface": {"color-scheme": "prefer-dark", "x": True}},
    "git_repos": ["https://github.com/me/dots.git", "git@github.com:me/other.git"],
}


@pytest.fixture(autouse=True)
def no_system_files(monkeypatch, tmp_path):
    monkeypatch.setattr(validate, "LOCALES", tmp_path / "missing")
    monkeypatch.setattr(validate, "ZONEINFO", tmp_path / "missing")


def with_(**changes) -> dict:
    data = copy.deepcopy(VALID)
    data.update(changes)
    return data


def test_valid_manifest_has_no_problems():
    assert validate.validate(VALID) == []


def test_repo_manifest_is_valid():
    assert validate.validate(manifest.load(paths.MANIFEST)) == []


def test_unknown_top_level_key():
    assert validate.validate(with_(system_service=["x"])) == ["system_service: unknown key"]


def test_disk_is_not_a_manifest_key():
    assert validate.validate(with_(disk="/dev/sda")) == ["disk: unknown key"]


def test_hostname_is_not_a_manifest_key():
    assert validate.validate(with_(hostname="midgard")) == ["hostname: unknown key"]


def test_every_problem_is_reported():
    data = with_(username=None, packages=["Bad"], gsettings=[])
    assert len(validate.validate(data)) == 3


@pytest.mark.parametrize(
    ("value", "problem"),
    [(None, "username: missing"), ("", "username: must be a non-empty string")],
)
def test_config_keys_required(value, problem):
    data = with_(username=value)
    if value is None:
        del data["username"]
    assert validate.validate(data) == [problem]


def test_config_key_must_be_string():
    assert validate.validate(with_(keymap=1)) == ["keymap: must be a non-empty string"]


@pytest.mark.parametrize("name", ["Foo", "-foo", ".foo", "foo bar", "foo/bar"])
def test_invalid_package_name(name):
    assert validate.validate(with_(packages=[name])) == [
        f"packages[0]: {name!r} is not a valid package name"
    ]


def test_package_section_must_be_list_of_strings():
    assert validate.validate(with_(packages="foot")) == ["packages: must be a list"]
    assert validate.validate(with_(packages=[{"a": 1}])) == [
        "packages[0]: must be a non-empty string"
    ]


def test_duplicate_within_section():
    assert validate.validate(with_(packages=["foot", "foot"])) == [
        "packages[1]: 'foot' is already listed at packages[0]"
    ]


def test_duplicate_across_sections():
    assert validate.validate(with_(packages=["git"])) == [
        "packages[0]: 'git' is already listed at pacstrap[1]"
    ]


def test_duplicate_url_package():
    data = with_(url_packages=[{"name": "foot", "url": "https://x/foot.pkg"}], packages=["foot"])
    assert validate.validate(data) == [
        "url_packages[0].name: 'foot' is already listed at packages[0]"
    ]


def test_duplicate_service():
    assert validate.validate(with_(user_services=["a", "a"])) == [
        "user_services[1]: 'a' is already listed at user_services[0]"
    ]


def test_url_package_needs_https():
    data = with_(url_packages=[{"name": "tool", "url": "http://x/tool.pkg"}])
    assert validate.validate(data) == ["url_packages[0].url: must start with https://"]


def test_url_package_fields():
    data = with_(url_packages=[{"name": "tool", "link": "https://x"}])
    assert validate.validate(data) == [
        "url_packages[0].link: unknown key",
        "url_packages[0].url: must be a non-empty string",
    ]


def test_url_packages_must_be_mappings():
    assert validate.validate(with_(url_packages=["tool"])) == ["url_packages[0]: must be a mapping"]


def test_pacman_key_fingerprint():
    data = with_(pacman_keys=[{"key": "ABCD", "server": "s"}])
    assert validate.validate(data) == ["pacman_keys[0].key: must be a 40 character hex fingerprint"]


def test_pacman_key_needs_server():
    data = with_(pacman_keys=[{"key": VALID["pacman_keys"][0]["key"]}])
    assert validate.validate(data) == ["pacman_keys[0].server: must be a non-empty string"]


def test_gsettings_shape():
    assert validate.validate(with_(gsettings=["x"])) == [
        "gsettings: must be a mapping of schema to keys"
    ]
    assert validate.validate(with_(gsettings={"s": "x"})) == [
        "gsettings.s: must be a mapping of key to value"
    ]
    assert validate.validate(with_(gsettings={"s": {"k": None}})) == [
        "gsettings.s.k: must be a string, number or boolean"
    ]


def test_git_repo_url():
    data = with_(git_repos=["https://github.com/me/dots.git", "/home/me/repo"])
    assert validate.validate(data) == [
        "git_repos[1]: '/home/me/repo' is not a git URL (https://, ssh:// or git@)"
    ]


def test_git_repos_include_install_repo():
    data = with_(git_repos=["https://github.com/me/other.git"])
    assert validate.validate(data) == ["git_repos: must include the install_repo 'dots'"]


def test_supported_locales_reads_arch_and_debian_formats():
    arch = "SUPPORTED-LOCALES=\\\nen_US.UTF-8/UTF-8 \\\nen_US/ISO-8859-1 \\\n"
    debian = "en_US.UTF-8 UTF-8\nfi_FI ISO-8859-1\n"
    assert {"en_US.UTF-8", "en_US"} <= supported_locales(arch)
    assert {"en_US.UTF-8", "fi_FI"} <= supported_locales(debian)


def test_locale_checked_when_list_present(monkeypatch, tmp_path):
    locales = tmp_path / "SUPPORTED"
    locales.write_text("en_US.UTF-8/UTF-8 \\\n")
    monkeypatch.setattr(validate, "LOCALES", locales)
    assert validate.validate(VALID) == []
    assert validate.validate(with_(locale="xx_XX.UTF-8")) == [
        "locale: 'xx_XX.UTF-8' is not a supported locale"
    ]


def test_timezone_checked_when_zoneinfo_present(monkeypatch, tmp_path):
    (tmp_path / "zoneinfo" / "Europe").mkdir(parents=True)
    (tmp_path / "zoneinfo" / "Europe" / "Helsinki").write_text("")
    monkeypatch.setattr(validate, "ZONEINFO", tmp_path / "zoneinfo")
    assert validate.validate(VALID) == []
    for zone in ("Europe/Nowhere", "Europe", "../zoneinfo/Europe/Helsinki"):
        assert validate.validate(with_(timezone=zone)) == [
            f"timezone: {zone!r} is not a known timezone"
        ]


def test_skipped_checks_are_reported():
    assert len(validate.skipped_checks()) == 2


def test_aur_packages_found():
    data = with_(aur_packages=["yay-bin"], aur_helpers=["yay-bin-debug"])
    assert check_aur_packages(data, lookup=lambda names: {"yay-bin"}) == []


def test_aur_package_missing():
    data = with_(aur_packages=["yay-bin", "nope"])
    assert check_aur_packages(data, lookup=lambda names: {"yay-bin"}) == [
        "aur_packages: 'nope' not found on the AUR"
    ]


def test_aur_unreachable_is_a_problem():
    def offline(names):
        raise OSError("network is unreachable")

    assert check_aur_packages(VALID, lookup=offline) == [
        "AUR packages not checked: network is unreachable"
    ]


def test_repo_packages_missing(monkeypatch):
    monkeypatch.setattr(validate.shutil, "which", lambda name: "/usr/bin/pacman")
    monkeypatch.setattr(validate, "describe", lambda names, flags: {n: "" for n in names[1:]})
    data = with_(packages=[], post_chroot=[])
    assert validate.check_repo_packages(data) == ["pacstrap: 'base' not found in the sync repos"]


def test_repo_packages_need_pacman(monkeypatch):
    monkeypatch.setattr(validate.shutil, "which", lambda name: None)
    assert validate.check_repo_packages(VALID) == [
        "packages not checked against the repos: pacman not found"
    ]


def test_empty_profile_is_valid():
    assert validate.validate_profile({}, ["a"]) == []


@pytest.mark.parametrize("key", ["hostname", "disk", "bogus"])
def test_profile_unknown_keys(key):
    assert validate.validate_profile({key: "x"}, ["a"]) == [f"{key}: unknown key"]


def test_profile_needs_no_required_keys():
    assert validate.validate_profile({"keymap": "fi", "install_repo": "other"}, []) == []


def test_profile_sections_are_checked():
    assert validate.validate_profile({"packages": ["Bad"]}, []) == [
        "packages[0]: 'Bad' is not a valid package name"
    ]


@pytest.mark.parametrize("value", ["b", ["b"], ["b", "c"], None])
def test_profile_extends_known_profiles(value):
    assert validate.validate_profile({"extends": value}, ["a", "b", "c"]) == []


@pytest.mark.parametrize(
    ("value", "problem"),
    [
        ("x", "extends: unknown profile 'x'; profiles in profiles/: a, b"),
        (["b", "x"], "extends[1]: unknown profile 'x'; profiles in profiles/: a, b"),
        ([1], "extends[0]: must be a non-empty string"),
        ("", "extends: must be a profile name or a list of profile names"),
        ({"b": 1}, "extends: must be a profile name or a list of profile names"),
    ],
)
def test_profile_extends_problems(value, problem):
    assert validate.validate_profile({"extends": value}, ["a", "b"]) == [problem]
