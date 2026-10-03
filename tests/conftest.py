import os

# Typer and rich force colour when these are set (GITHUB_ACTIONS in CI), which splits
# words like --hostname with escape codes. They are read at import, so clear them before
# any test module imports the installer.
for var in ("FORCE_COLOR", "GITHUB_ACTIONS", "PY_COLORS", "TTY_COMPATIBLE"):
    os.environ.pop(var, None)
