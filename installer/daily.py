from installer.config import Config
from installer.customize import customize
from installer.packages import packages
from installer.projects import user_projects
from installer.shell import echo


def daily(cfg: Config, data: dict) -> None:
    echo("==> Updating packages...")
    packages(data)

    echo("==> Setting up user projects...")
    user_projects(cfg, data)

    echo("==> Running user customisations...")
    customize(data)
