from pathlib import Path

from installer import manifest
from installer.config import Config
from installer.shell import echo, run


def user_projects(cfg: Config, data: dict) -> None:
    projects_dir = Path.home() / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    for repo in manifest.section(data, "git_repos"):
        name = repo.rsplit("/", 1)[-1].removesuffix(".git")
        if (projects_dir / name).is_dir():
            echo(f"Skipping {name} (already exists)")
            continue
        echo(f"Cloning {repo}...")
        run("git", "clone", repo, str(projects_dir / name))

    dotfiles_dir = projects_dir / cfg.install_repo / "dotfiles"
    if dotfiles_dir.is_dir():
        echo("Running make in dotfiles...")
        run("make", "-C", str(dotfiles_dir))
