from pathlib import Path

CPUINFO = Path("/proc/cpuinfo")
UCODE_BY_VENDOR = {"GenuineIntel": "intel-ucode", "AuthenticAMD": "amd-ucode"}


def vendor(cpuinfo: str) -> str | None:
    for line in cpuinfo.splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "vendor_id":
            return value.strip()
    return None


def ucode(cpuinfo: str | None = None) -> str | None:
    """Microcode package for this CPU, or None when the vendor has no Arch package."""
    if cpuinfo is None:
        cpuinfo = CPUINFO.read_text()
    return UCODE_BY_VENDOR.get(vendor(cpuinfo) or "")
