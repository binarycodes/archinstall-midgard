import os
import shlex
import subprocess
import sys
from pathlib import Path


def echo(message: str) -> None:
    print(message, flush=True)


def run(
    *args: str, check: bool = True, capture: bool = False, **kwargs
) -> subprocess.CompletedProcess:
    print("+", shlex.join(args), file=sys.stderr, flush=True)
    return subprocess.run(args, check=check, text=True, capture_output=capture, **kwargs)


def output(*args: str, check: bool = True, **kwargs) -> str:
    return run(*args, check=check, capture=True, **kwargs).stdout


def write_file(path: Path | str, text: str) -> None:
    print("+ write", path, file=sys.stderr, flush=True)
    Path(path).write_text(text)


def append_file(path: Path | str, text: str) -> None:
    print("+ append", path, file=sys.stderr, flush=True)
    with open(path, "a") as f:
        f.write(text)


def require_root() -> None:
    if os.geteuid() != 0:
        sys.exit("Error: this step must run as root.")


def require_user() -> None:
    if os.geteuid() == 0:
        sys.exit("Error: Do not run this step as root.")
