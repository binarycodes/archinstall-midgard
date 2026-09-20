from installer import boot

EFIBOOTMGR = """\
BootCurrent: 0002
Timeout: 1 seconds
BootOrder: 0002,0001,0000
Boot0000* Windows Boot Manager\tHD(1,GPT,...)
Boot0001* Arch Linux LTS\tHD(1,GPT,...)
Boot0002* Arch Linux\tHD(1,GPT,...)
Boot0003  UEFI: Built-in EFI Shell\tFvVol(...)
"""


def test_parse_entries_skips_header_lines():
    assert [n for n, _ in boot.parse_entries(EFIBOOTMGR)] == ["0000", "0001", "0002", "0003"]


def test_arch_entries():
    assert boot.arch_entries(boot.parse_entries(EFIBOOTMGR)) == ["0001", "0002"]


def test_boot_order_puts_arch_then_lts_then_others():
    assert boot.boot_order(boot.parse_entries(EFIBOOTMGR)) == ["0002", "0001", "0000", "0003"]


def test_kernel_options_match_the_script():
    assert boot.kernel_options("intel-ucode", "linux-lts", "abcd") == (
        "initrd=\\intel-ucode.img initrd=\\initramfs-linux-lts.img "
        "root=UUID=abcd rw quiet loglevel=3"
    )


def test_boot_files_use_ucode():
    assert "/boot/amd-ucode.img" in boot.boot_files("amd-ucode")
