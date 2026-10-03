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
