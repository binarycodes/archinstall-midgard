import pytest

from installer import hardware
from installer.hardware import FEATURES, detect_features

THINKPAD_INPUT = """\
I: Bus=0019 Vendor=0000 Product=0005 Version=0000
N: Name="Lid Switch"
P: Phys=PNP0C0D/button/input0

I: Bus=0011 Vendor=0001 Product=0001 Version=ab54
N: Name="AT Translated Set 2 keyboard"
P: Phys=isa0060/serio0/input0

I: Bus=0011 Vendor=0002 Product=0007 Version=01b1
N: Name="SynPS/2 Synaptics TouchPad"
P: Phys=isa0060/serio1/input0

I: Bus=0011 Vendor=0002 Product=000a Version=0000
N: Name="TPPS/2 Elan TrackPoint"
P: Phys=synaptics-pt/serio0/input0
"""

ELAN_INPUT = """\
I: Bus=0018 Vendor=04f3 Product=3195 Version=0100
N: Name="ELAN0678:00 04F3:3195 Touchpad"
"""

DESKTOP_INPUT = """\
I: Bus=0019 Vendor=0000 Product=0001 Version=0000
N: Name="Power Button"
P: Phys=LNXPWRBN/button/input0

I: Bus=0003 Vendor=046d Product=c08b Version=0111
N: Name="Logitech G502 HERO Gaming Mouse"
P: Phys=usb-0000:0c:00.0-3/input0
"""

# (class, vendor) of real PCI devices
THINKPAD_PCI = [
    ("0x060000", "0x8086"),  # host bridge
    ("0x030000", "0x8086"),  # Iris Xe graphics
    ("0x040380", "0x8086"),  # audio
    ("0x028000", "0x8086"),  # wifi
]
DESKTOP_PCI = [
    ("0x060000", "0x1022"),  # AMD host bridge
    ("0x030000", "0x1002"),  # Radeon RX 7900 XTX
    ("0x040300", "0x1002"),  # its HDMI audio
    ("0x020000", "0x8086"),  # Intel I225-V ethernet: Intel, but not a GPU
]
HYBRID_PCI = [
    ("0x030000", "0x8086"),  # Intel iGPU
    ("0x038000", "0x1002"),  # AMD dGPU, listed as "display controller"
]
NVIDIA_PCI = [("0x030000", "0x10de"), ("0x040300", "0x10de")]


def test_battery():
    assert hardware.battery([("Mains", ""), ("Battery", "")])  # ThinkPad AC and BAT0
    assert not hardware.battery([])
    assert not hardware.battery([("USB", "")])


def test_peripheral_battery_is_not_the_machines():
    # a wireless mouse on the desktop (solaar's hidpp_battery_0)
    assert not hardware.battery([("Battery", "Device")])


def test_kbd_backlight():
    thinkpad = ["input3::capslock", "platform::micmute", "tpacpi::kbd_backlight"]
    assert hardware.kbd_backlight(thinkpad)
    assert hardware.kbd_backlight(["dell::kbd_backlight"])
    assert not hardware.kbd_backlight(["input2::capslock", "input2::numlock"])


@pytest.mark.parametrize(
    ("devices", "expected"), [(THINKPAD_INPUT, True), (ELAN_INPUT, True), (DESKTOP_INPUT, False)]
)
def test_touchpad(devices, expected):
    assert hardware.touchpad(devices) is expected


def test_touchpad_only_matches_device_names():
    assert not hardware.touchpad('I: Bus=0011\nP: Phys=touchpad/input0\nN: Name="Keyboard"\n')


@pytest.mark.parametrize(
    ("pci", "intel", "amd"),
    [
        (THINKPAD_PCI, True, False),
        (DESKTOP_PCI, False, True),
        (HYBRID_PCI, True, True),
        (NVIDIA_PCI, False, False),
        ([], False, False),
    ],
)
def test_gpus(pci, intel, amd):
    assert hardware.gpu_intel(pci) is intel
    assert hardware.gpu_amd(pci) is amd


def test_listing_detectors():
    for detector in (hardware.backlight, hardware.lid, hardware.wifi, hardware.bluetooth):
        assert detector(["x"])
        assert not detector([])


def write_tree(root, files: dict[str, str]):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        if path.endswith("/"):
            (root / path).mkdir(exist_ok=True)
        else:
            (root / path).write_text(text)
    return root


def pci_files(devices):
    files = {}
    for i, (cls, vendor) in enumerate(devices):
        files[f"sys/bus/pci/devices/0000:00:{i:02x}.0/class"] = f"{cls}\n"
        files[f"sys/bus/pci/devices/0000:00:{i:02x}.0/vendor"] = f"{vendor}\n"
    return files


def test_detect_features_on_a_thinkpad(tmp_path):
    root = write_tree(
        tmp_path,
        {
            "sys/class/power_supply/AC/type": "Mains\n",
            "sys/class/power_supply/BAT0/type": "Battery\n",
            "sys/class/backlight/intel_backlight/": "",
            "sys/class/leds/tpacpi::kbd_backlight/": "",
            "sys/class/leds/input3::capslock/": "",
            "proc/bus/input/devices": THINKPAD_INPUT,
            "proc/acpi/button/lid/LID/": "",
            "sys/class/net/lo/": "",
            "sys/class/net/wlan0/wireless/": "",
            "sys/class/bluetooth/hci0/": "",
            **pci_files(THINKPAD_PCI),
        },
    )
    assert detect_features(root) == list(FEATURES[:-1])  # everything but gpu_amd


def test_detect_features_on_the_desktop(tmp_path):
    root = write_tree(
        tmp_path,
        {
            "sys/class/power_supply/hidpp_battery_0/type": "Battery\n",
            "sys/class/power_supply/hidpp_battery_0/scope": "Device\n",
            "sys/class/leds/input2::capslock/": "",
            "proc/bus/input/devices": DESKTOP_INPUT,
            "sys/class/net/lo/": "",
            "sys/class/net/enp9s0/": "",
            **pci_files(DESKTOP_PCI),
        },
    )
    assert detect_features(root) == ["gpu_amd"]


def test_detect_features_with_nothing_to_read(tmp_path):
    assert detect_features(tmp_path) == []
