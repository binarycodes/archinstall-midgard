import pytest

from installer import manifest, paths
from installer.config import Config


def test_partitions_derive_from_disk():
    cfg = Config.from_manifest(manifest.load(paths.MANIFEST))
    assert (cfg.efi, cfg.swap, cfg.root) == (
        cfg.partition(1),
        cfg.partition(2),
        cfg.partition(3),
    )


@pytest.mark.parametrize(
    ("disk", "expected"),
    [
        ("/dev/nvme0n1", "/dev/nvme0n1p1"),
        ("/dev/mmcblk0", "/dev/mmcblk0p1"),
        ("/dev/sda", "/dev/sda1"),
        ("/dev/vda", "/dev/vda1"),
    ],
)
def test_partition_separator_follows_kernel_naming(disk, expected):
    cfg = Config(
        username="u",
        hostname="h",
        timezone="t",
        locale="l",
        keymap="k",
        install_repo="r",
        disk=disk,
    )
    assert cfg.partition(1) == expected
