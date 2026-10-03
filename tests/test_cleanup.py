from installer.cleanup import orphaned_packages


def test_orphaned_packages_is_set_difference():
    data = {"packages": ["vim", "git"], "aur_helpers": ["yay-bin"]}
    assert orphaned_packages("git\nvim\nyay-bin\nstray\n", data) == ["stray"]


def test_detected_ucode_is_not_orphaned():
    data = {"packages": ["vim"]}
    assert orphaned_packages("vim\nintel-ucode\n", data, "intel-ucode") == []
    assert orphaned_packages("vim\nintel-ucode\n", data) == ["intel-ucode"]
