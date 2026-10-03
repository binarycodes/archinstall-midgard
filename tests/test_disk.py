import io
import json
from dataclasses import replace

import pytest
from rich.console import Console

from installer import disk
from installer.disk import Disk, DiskError, Partition

GIB = 1024**3


def device(name, size_gib, type_="disk", children=(), mountpoints=(None,), **extra):
    return {
        "name": name,
        "path": f"/dev/{name}",
        "type": type_,
        "size": int(size_gib * GIB),
        "model": extra.pop("model", None),
        "serial": extra.pop("serial", None),
        "tran": extra.pop("tran", None),
        "ro": extra.pop("ro", False),
        "fstype": extra.pop("fstype", None),
        "label": extra.pop("label", None),
        "mountpoints": list(mountpoints),
        **({"children": list(children)} if children else {}),
    }


LSBLK = json.dumps(
    {
        "blockdevices": [
            device(
                "loop0", 0.8, type_="loop", fstype="squashfs", mountpoints=["/run/archiso/airootfs"]
            ),
            device(
                "sda",
                28.9,
                model="SanDisk Ultra ",
                tran="usb",
                fstype="iso9660",
                children=[
                    device(
                        "sda1",
                        1.2,
                        type_="part",
                        label="ARCH_202510",
                        mountpoints=["/run/archiso/bootmnt"],
                    ),
                    device("sda2", 0.2, type_="part", fstype="vfat"),
                ],
            ),
            device("sr0", 1.0, type_="rom"),
            device("zram0", 4.0, mountpoints=["[SWAP]"]),
            device("mmcblk0", 0, tran="mmc"),
            device("sdb", 100, ro="1", tran="usb"),
            device(
                "nvme0n1",
                476.9,
                model="Samsung SSD 980 PRO 512GB",
                serial="S5GXNX0T123456",
                tran="nvme",
                children=[
                    device("nvme0n1p1", 1, type_="part", fstype="vfat"),
                    device("nvme0n1p2", 33, type_="part", fstype="swap"),
                    device("nvme0n1p3", 442.9, type_="part", fstype="btrfs"),
                ],
            ),
        ]
    }
)


def nvme(**changes) -> Disk:
    found = next(d for d in disk.parse_lsblk(LSBLK) if d.name == "nvme0n1")
    return replace(found, **changes)


def test_parse_lsblk_keeps_only_disks():
    names = [d.name for d in disk.parse_lsblk(LSBLK)]
    assert names == ["sda", "zram0", "mmcblk0", "sdb", "nvme0n1"]


def test_parse_lsblk_reads_partitions_and_fields():
    d = nvme()
    assert (d.model, d.serial, d.tran, d.read_only) == (
        "Samsung SSD 980 PRO 512GB",
        "S5GXNX0T123456",
        "nvme",
        False,
    )
    assert [p.name for p in d.partitions] == ["nvme0n1p1", "nvme0n1p2", "nvme0n1p3"]
    assert d.partitions[0].fstype == "vfat"
    assert d.mountpoints == ()


def test_candidates_skip_iso_medium_zram_empty_and_read_only():
    found = [d.name for d in disk.parse_lsblk(LSBLK) if disk.is_candidate(d)]
    assert found == ["nvme0n1"]


def test_old_lsblk_read_only_flag():
    assert disk.parse_lsblk(LSBLK)[3].read_only  # sdb, "ro": "1"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/dev/nvme0n1", "/dev/nvme0n1p1"),
        ("/dev/mmcblk0", "/dev/mmcblk0p1"),
        ("/dev/sda", "/dev/sda1"),
        ("/dev/vda", "/dev/vda1"),
    ],
)
def test_partition_separator_follows_kernel_naming(path, expected):
    assert disk.partition_path(path, 1) == expected


def test_layout_partitions():
    d = nvme()
    assert (d.efi, d.swap, d.root) == ("/dev/nvme0n1p1", "/dev/nvme0n1p2", "/dev/nvme0n1p3")


def test_stable_id_prefers_model_serial_links(tmp_path):
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "nvme0n1").touch()
    (dev / "nvme0n1p1").touch()
    by_id = tmp_path / "by-id"
    by_id.mkdir()
    for name, target in [
        ("nvme-eui.002538b", "nvme0n1"),
        ("nvme-Samsung_SSD_980_S5GX", "nvme0n1"),
        ("nvme-Samsung_SSD_980_S5GX-part1", "nvme0n1p1"),
        ("wwn-0x5002538", "nvme0n1"),
    ]:
        (by_id / name).symlink_to(dev / target)
    assert disk.stable_id("nvme0n1", by_id) == str(by_id / "nvme-Samsung_SSD_980_S5GX")
    assert disk.stable_id("sda", by_id) is None
    assert disk.stable_id("nvme0n1", tmp_path / "missing") is None


def test_problems_none_for_a_good_disk():
    assert disk.problems(nvme(), swap_gib=33) == []


def test_problems_too_small():
    small = nvme(size=60 * GIB)
    assert disk.problems(small, swap_gib=33) == [
        "/dev/nvme0n1 is 60.0 GiB; at least 66 GiB is needed (1 EFI + 33 swap + 32 root)"
    ]


def partitions_mounted_at(*mounts: str) -> tuple[Partition, ...]:
    return tuple(
        Partition(f"nvme0n1p{i}", f"/dev/nvme0n1p{i}", GIB, None, None, (m,))
        for i, m in enumerate(mounts, start=1)
    )


def test_problems_mounted_elsewhere():
    busy = nvme(partitions=partitions_mounted_at("/home", "/mntx"))
    assert disk.problems(busy, swap_gib=1) == ["/dev/nvme0n1 is in use, mounted at /home, /mntx"]


def test_leftovers_from_an_earlier_attempt_are_not_problems():
    leftover = nvme(partitions=partitions_mounted_at("/mnt/boot", "[SWAP]", "/mnt"))
    assert disk.problems(leftover, swap_gib=1) == []
    assert leftover.swaps() == ["/dev/nvme0n1p2"]


def render(renderable) -> str:
    console = Console(width=200, record=True, file=io.StringIO())
    console.print(renderable)
    return console.export_text()


def test_layout_table():
    text = render(disk.layout_table(nvme(), swap_gib=33))
    rows = [line.split() for line in text.splitlines() if line.strip().startswith("/dev/")]
    assert rows == [
        ["/dev/nvme0n1p1", "EFI", "1.0", "GiB", "vfat", "/boot"],
        ["/dev/nvme0n1p2", "swap", "33.0", "GiB", "swap", "-"],
        ["/dev/nvme0n1p3", "root", "~442.9", "GiB", "btrfs", "/"],
    ]


def test_layout_table_never_shows_negative_root():
    assert "~0.0 GiB" in render(disk.layout_table(nvme(size=10 * GIB), swap_gib=33))


class Answers:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.questions = []

    def __call__(self, question):
        self.questions.append(question)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


@pytest.fixture
def machine(monkeypatch):
    """Two candidate disks."""
    sda = replace(nvme(), name="sda", path="/dev/sda", tran="sata", size=1000 * GIB)
    monkeypatch.setattr(disk, "candidates", lambda: [nvme(), sda])


def test_select_disk_returns_confirmed_choice(machine):
    answers = Answers("2", "sda")
    chosen = disk.select_disk(33, ask=answers)
    assert chosen.path == "/dev/sda"
    assert answers.questions[1] == 'Type "[bold]sda[/]" to confirm: '


def test_contents_table_lists_partitions():
    text = render(disk.contents_table(nvme(partitions=partitions_mounted_at("/mnt", "[SWAP]"))))
    rows = [line.split() for line in text.splitlines() if line.strip().startswith("/dev/")]
    assert rows == [
        ["/dev/nvme0n1p1", "1.0", "GiB", "-", "-", "/mnt"],
        ["/dev/nvme0n1p2", "1.0", "GiB", "-", "-", "[SWAP]"],
    ]


def test_contents_table_of_empty_and_whole_disk_filesystems():
    assert "no partitions" in render(disk.contents_table(nvme(partitions=())))
    iso = next(d for d in disk.parse_lsblk(LSBLK) if d.name == "sda")
    text = render(disk.contents_table(iso))
    assert "iso9660" in text
    assert "ARCH_202510" in text
    assert "/run/archiso/bootmnt" in text


def test_disks_table_and_details_escape_markup():
    odd = nvme(model="Disk [bold]X[/]", by_id="/dev/disk/by-id/[x]")
    assert "Disk [bold]X[/]" in render(disk.disks_table([odd]))
    assert "/dev/disk/by-id/[x]" in render(disk.details(odd))


@pytest.mark.parametrize("answers", [("q",), ("",), ()])
def test_select_disk_quit(machine, answers):
    with pytest.raises(DiskError, match="no disk selected"):
        disk.select_disk(33, ask=Answers(*answers))


@pytest.mark.parametrize("confirmation", ["y", "yes", "/dev/nvme0n1", "NVME0N1", ""])
def test_select_disk_needs_exact_name(machine, confirmation):
    with pytest.raises(DiskError, match="not confirmed"):
        disk.select_disk(33, ask=Answers("1", confirmation))


def test_select_disk_refuses_unusable_disk_before_confirmation(machine, capsys):
    answers = Answers("1", "nvme0n1")
    with pytest.raises(DiskError, match="at least"):
        disk.select_disk(500, ask=answers)
    assert len(answers.questions) == 1
    out = capsys.readouterr().out
    assert out.index("Current contents") < out.index("New layout")
    assert "erased" not in out


def test_select_disk_without_candidates(monkeypatch):
    monkeypatch.setattr(disk, "candidates", list)
    with pytest.raises(DiskError, match="no disks"):
        disk.select_disk(33, ask=Answers())


def test_boot_partition_from_boot_mount(monkeypatch, tmp_path):
    outputs = {
        ("findmnt", "-n", "-o", "SOURCE", "/boot"): "/dev/nvme0n1p1\n",
        ("lsblk", "-n", "-d", "-o", "PKNAME", "/dev/nvme0n1p1"): "nvme0n1\n",
    }
    monkeypatch.setattr(disk, "output", lambda *args, **kwargs: outputs[args])
    (tmp_path / "nvme0n1p1").mkdir()
    (tmp_path / "nvme0n1p1" / "partition").write_text("1\n")
    monkeypatch.setattr(disk, "SYS_BLOCK", tmp_path)
    assert disk.boot_partition() == ("/dev/nvme0n1", 1)


def test_boot_partition_needs_boot_mounted(monkeypatch):
    monkeypatch.setattr(disk, "output", lambda *args, **kwargs: "")
    with pytest.raises(DiskError, match="/boot is not mounted"):
        disk.boot_partition()
