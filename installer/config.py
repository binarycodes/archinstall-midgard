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

    @property
    def efi(self) -> str:
        return f"{self.disk}p1"

    @property
    def swap(self) -> str:
        return f"{self.disk}p2"

    @property
    def root(self) -> str:
        return f"{self.disk}p3"
