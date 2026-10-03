import math
from pathlib import Path

from installer.config import SWAP_SPARE_GIB

MEMINFO = Path("/proc/meminfo")


def total_gib(meminfo: str | None = None) -> float:
    """RAM usable by the kernel (MemTotal), a little under what is physically installed."""
    if meminfo is None:
        meminfo = MEMINFO.read_text()
    for line in meminfo.splitlines():
        key, _, value = line.partition(":")
        if key == "MemTotal":
            # /proc/meminfo says "kB" but means KiB
            return int(value.split()[0]) / 1024**2
    raise ValueError("MemTotal not found in meminfo")


def swap_gib(ram_gib: float) -> int:
    return math.ceil(ram_gib + SWAP_SPARE_GIB)
