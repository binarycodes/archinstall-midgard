import pytest

from installer import memory


def test_total_gib_reads_memtotal_in_kib():
    meminfo = "MemTotal:       32571896 kB\nMemFree:         1048576 kB\n"
    assert memory.total_gib(meminfo) == pytest.approx(31.06, abs=0.01)


def test_total_gib_without_memtotal():
    with pytest.raises(ValueError):
        memory.total_gib("MemFree: 1 kB\n")
