from dataclasses import dataclass, fields


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    username: str
    hostname: str
    timezone: str
    locale: str
    keymap: str
    install_repo: str
    disk: str
    swap_size: str
    ucode: str

    @classmethod
    def from_manifest(cls, data: dict) -> "Config":
        names = [f.name for f in fields(cls)]
        missing = [name for name in names if not data.get(name)]
        if missing:
            raise ConfigError("manifest is missing config keys: " + ", ".join(missing))
        return cls(**{name: str(data[name]) for name in names})

    def partition(self, number: int) -> str:
        # The kernel inserts "p" only when the disk name ends in a digit
        # (nvme0n1p1, mmcblk0p1), never otherwise (sda1, vda1).
        separator = "p" if self.disk[-1].isdigit() else ""
        return f"{self.disk}{separator}{number}"

    @property
    def efi(self) -> str:
        return self.partition(1)

    @property
    def swap(self) -> str:
        return self.partition(2)

    @property
    def root(self) -> str:
        return self.partition(3)
