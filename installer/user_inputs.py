"""Everything the install asks the user, collected up front so the rest runs unattended."""

from collections.abc import Callable
from dataclasses import dataclass

from rich.markup import escape

from installer.disk import Disk, DiskError, select_disk
from installer.shell import console


class InputError(ValueError):
    pass


@dataclass(frozen=True)
class UserInputs:
    disk: Disk
    passwords: dict[str, str]  # account → password


def hidden_input(question: str) -> str:
    return console.input(question, password=True)


def ask_password(account: str, ask: Callable[[str], str] | None = None) -> str:
    """A password for account, typed twice; asks again until both match."""
    ask = ask or hidden_input
    name = escape(account)
    while True:
        try:
            first = ask(f"Password for [bold]{name}[/]: ")
            if not first:
                console.print("[yellow]Enter a password.[/]")
                continue
            second = ask(f"Repeat the password for [bold]{name}[/]: ")
        except EOFError:
            raise InputError(f"no password given for {account}") from None
        if first == second:
            return first
        console.print("[yellow]The passwords did not match. Try again.[/]")


def collect(swap_gib: int, username: str) -> UserInputs:
    """Ask for the disk to erase, then the root and user passwords, in that order."""
    try:
        disk = select_disk(swap_gib)
    except DiskError as e:
        raise InputError(str(e)) from None
    console.print()
    passwords = {account: ask_password(account) for account in ("root", username)}
    return UserInputs(disk, passwords)
