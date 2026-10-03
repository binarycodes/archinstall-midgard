"""Hardware features of this machine, one per capability.

Each detector is a pure function over text or a directory listing; detect_features()
reads those from the running system.
"""

import re
from pathlib import Path

# Every known feature, in the order their files are merged
FEATURES = (
    "battery",
    "backlight",
    "kbd_backlight",
    "touchpad",
    "lid",
    "wifi",
    "bluetooth",
    "gpu_intel",
    "gpu_amd",
)

INTEL = "0x8086"
AMD = "0x1002"
DISPLAY_CLASS = "0x03"  # PCI base class of VGA, 3D and other display controllers
DEVICE_NAME = re.compile(r'^N: Name="(?P<name>.*)"$')


def battery(supplies: list[tuple[str, str]]) -> bool:
    """supplies: (type, scope) of each power supply.

    Wireless mice and keyboards report their own battery with scope Device; only a
    battery powering the machine counts.
    """
    return any(kind == "Battery" and scope != "Device" for kind, scope in supplies)


def backlight(entries: list[str]) -> bool:
    return bool(entries)


def kbd_backlight(leds: list[str]) -> bool:
    return any(led.endswith("::kbd_backlight") for led in leds)


def touchpad(devices: str) -> bool:
    """devices: /proc/bus/input/devices. Matches like the sleep hook: any case, e.g. TouchPad."""
    for line in devices.splitlines():
        m = DEVICE_NAME.match(line.strip())
        if m and "touchpad" in m.group("name").lower():
            return True
    return False


def lid(entries: list[str]) -> bool:
    return bool(entries)


def wifi(wireless_interfaces: list[str]) -> bool:
    return bool(wireless_interfaces)


def bluetooth(entries: list[str]) -> bool:
    return bool(entries)


def has_display_controller(pci_devices: list[tuple[str, str]], vendor: str) -> bool:
    """pci_devices: (class, vendor) of each PCI device, as sysfs writes them (0x030000, 0x8086)."""
    return any(
        cls.startswith(DISPLAY_CLASS) and dev_vendor == vendor for cls, dev_vendor in pci_devices
    )


def gpu_intel(pci_devices: list[tuple[str, str]]) -> bool:
    return has_display_controller(pci_devices, INTEL)


def gpu_amd(pci_devices: list[tuple[str, str]]) -> bool:
    return has_display_controller(pci_devices, AMD)


def listing(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir()) if directory.is_dir() else []


def read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def detect_features(root: Path = Path("/")) -> list[str]:
    """The features found on this machine, in the order of FEATURES."""
    sys_class = root / "sys" / "class"
    supplies = sys_class / "power_supply"
    pci = root / "sys" / "bus" / "pci" / "devices"
    pci_devices = [(read(pci / d / "class"), read(pci / d / "vendor")) for d in listing(pci)]
    try:
        devices = (root / "proc" / "bus" / "input" / "devices").read_text()
    except OSError:
        devices = ""
    found = {
        "battery": battery(
            [(read(supplies / s / "type"), read(supplies / s / "scope")) for s in listing(supplies)]
        ),
        "backlight": backlight(listing(sys_class / "backlight")),
        "kbd_backlight": kbd_backlight(listing(sys_class / "leds")),
        "touchpad": touchpad(devices),
        "lid": lid(listing(root / "proc" / "acpi" / "button" / "lid")),
        "wifi": wifi(
            [i for i in listing(sys_class / "net") if (sys_class / "net" / i / "wireless").is_dir()]
        ),
        "bluetooth": bluetooth(listing(sys_class / "bluetooth")),
        "gpu_intel": gpu_intel(pci_devices),
        "gpu_amd": gpu_amd(pci_devices),
    }
    return [feature for feature in FEATURES if found[feature]]
