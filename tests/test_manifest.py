import pytest

from installer import manifest, paths


def test_section_missing_is_empty():
    assert manifest.section({}, "packages") == []
    assert manifest.section({"packages": None}, "packages") == []


def test_managed_packages_unions_sections_and_url_names():
    data = {
        "pacstrap": ["base", "git"],
        "packages": ["git", "vim"],
        "aur_packages": ["yay-bin"],
        "url_packages": [{"name": "ssh-keysign", "url": "https://example/x.pkg"}],
        "system_services": ["iwd"],
    }
    assert manifest.managed_packages(data) == ["base", "git", "ssh-keysign", "vim", "yay-bin"]


def test_repo_manifest_loads():
    data = manifest.load(paths.MANIFEST)
    for name in manifest.PACKAGE_SECTIONS:
        assert manifest.section(data, name), name
    assert "python" in manifest.section(data, "pacstrap")
    assert "uv" in manifest.section(data, "pacstrap")


def test_duplicate_keys_are_rejected(tmp_path):
    path = tmp_path / "m.yml"
    path.write_text("username: a\nhostname: h\nusername: b\n")
    with pytest.raises(manifest.ManifestError, match="line 3: duplicate key 'username'"):
        manifest.load(path)


def test_duplicate_nested_keys_are_rejected(tmp_path):
    path = tmp_path / "m.yml"
    path.write_text("gsettings:\n  s:\n    k: 1\n    k: 2\n")
    with pytest.raises(manifest.ManifestError, match="duplicate key 'k'"):
        manifest.load(path)


@pytest.mark.parametrize("text", ["- a\n- b\n", "", "a: [\n"])
def test_load_rejects_non_mapping_and_bad_yaml(tmp_path, text):
    path = tmp_path / "m.yml"
    path.write_text(text)
    with pytest.raises(manifest.ManifestError):
        manifest.load(path)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/me/dots.git",
        "https://github.com/me/dots",
        "https://github.com/me/dots/",
        "git@github.com:me/dots.git",
    ],
)
def test_repo_name(url):
    assert manifest.repo_name(url) == "dots"


def test_load_reports_missing_file(tmp_path):
    with pytest.raises(manifest.ManifestError, match="cannot read"):
        manifest.load(tmp_path / "nope.yml")


def test_load_reports_yaml_error_line(tmp_path):
    path = tmp_path / "m.yml"
    path.write_text("a: 1\nb: [\n")
    with pytest.raises(manifest.ManifestError, match="line 3: invalid YAML"):
        manifest.load(path)


BASE = {
    "keymap": "us",
    "packages": ["foot", "sway"],
    "aur_helpers": None,
    "gsettings": {"iface": {"theme": "dark", "font": "Roboto"}},
}


def test_merge_with_an_empty_profile_is_exactly_the_base():
    assert manifest.merge(BASE, {}) == BASE


def test_merge_without_layers_is_the_base():
    assert manifest.merge(BASE) == BASE


def test_merge_later_single_value_wins():
    assert manifest.merge(BASE, {"keymap": "de"}, {"keymap": "fi"})["keymap"] == "fi"


def test_merge_mappings_key_by_key():
    merged = manifest.merge(BASE, {"gsettings": {"iface": {"font": "Noto"}, "other": {"k": 1}}})
    assert merged["gsettings"] == {
        "iface": {"theme": "dark", "font": "Noto"},
        "other": {"k": 1},
    }


def test_merge_lists_are_combined_without_duplicates():
    merged = manifest.merge(BASE, {"packages": ["vim", "foot"]}, {"packages": ["mpv", "vim"]})
    assert merged["packages"] == ["foot", "sway", "vim", "mpv"]


def test_merge_lists_of_mappings_drop_duplicates():
    key = {"key": "A" * 40, "server": "s"}
    merged = manifest.merge({"pacman_keys": [key]}, {"pacman_keys": [dict(key)]})
    assert merged["pacman_keys"] == [key]


def test_merge_empty_value_adds_nothing():
    assert manifest.merge(BASE, {"packages": None, "keymap": None}) == BASE


def test_merge_adds_new_sections():
    assert manifest.merge(BASE, {"aur_helpers": ["yay-bin"]})["aur_helpers"] == ["yay-bin"]


def test_merge_leaves_its_inputs_unchanged():
    profile = {"packages": ["vim"], "gsettings": {"iface": {"font": "Noto"}}}
    manifest.merge(BASE, profile)
    assert BASE["packages"] == ["foot", "sway"]
    assert BASE["gsettings"]["iface"]["font"] == "Roboto"


def test_load_allows_an_empty_file_only_when_asked(tmp_path):
    path = tmp_path / "p.yml"
    path.write_text("---\n")
    assert manifest.load(path, allow_empty=True) == {}
    with pytest.raises(manifest.ManifestError):
        manifest.load(path)


def test_repo_profiles_are_empty():
    for name in ("gaming", "workstation"):
        assert manifest.load(paths.REPO_ROOT / "profiles" / f"{name}.yml", allow_empty=True) == {}
