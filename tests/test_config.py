import pytest

from installer import manifest, paths
from installer.config import Config, ConfigError


def test_missing_keys_are_named():
    with pytest.raises(ConfigError, match="disk, swap_size, ucode"):
        Config.from_manifest(
            {
                "username": "u",
                "hostname": "h",
                "timezone": "t",
                "locale": "l",
                "keymap": "k",
                "install_repo": "r",
            }
        )


def test_partitions_derive_from_disk():
    cfg = Config.from_manifest(manifest.load(paths.MANIFEST))
    assert (cfg.efi, cfg.swap, cfg.root) == (
        f"{cfg.disk}p1",
        f"{cfg.disk}p2",
        f"{cfg.disk}p3",
    )
