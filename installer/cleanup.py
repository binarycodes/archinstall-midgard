from installer import manifest
from installer.shell import echo, output, run


def orphaned_packages(installed: str, data: dict) -> list[str]:
    return sorted(set(installed.split()) - set(manifest.managed_packages(data)))


def cleanup(data: dict) -> None:
    orphaned = orphaned_packages(output("pacman", "-Qqe"), data)
    if not orphaned:
        echo("No orphaned packages found.")
        return

    echo("Explicitly installed packages not in manifest.yml:\n")
    echo("\n".join(orphaned))
    echo("")
    if input("Remove these packages? [y/N] ").strip().lower() == "y":
        run("sudo", "pacman", "-Rcns", *orphaned)
