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
