import pytest

from installer import cpu


def cpuinfo(vendor_id: str) -> str:
    return f"processor\t: 0\nvendor_id\t: {vendor_id}\ncpu family\t: 6\n"


@pytest.mark.parametrize(
    ("vendor_id", "expected"),
    [
        ("GenuineIntel", "intel-ucode"),
        ("AuthenticAMD", "amd-ucode"),
        ("CentaurHauls", None),
    ],
)
def test_ucode_follows_vendor(vendor_id, expected):
    assert cpu.ucode(cpuinfo(vendor_id)) == expected


def test_ucode_without_vendor_line():
    # ARM's /proc/cpuinfo has no vendor_id
    assert cpu.ucode("processor\t: 0\nBogoMIPS\t: 48.00\n") is None
