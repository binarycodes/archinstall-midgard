import re

# A single RFC 1123 label: what systemd and most tools accept as a static hostname
LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def problem(name: str) -> str | None:
    """Why the hostname can't be used, or None when it is valid."""
    if LABEL.match(name):
        return None
    return (
        f"hostname {name!r} is not valid: use lowercase letters, digits and hyphens, "
        "not starting or ending with a hyphen, at most 63 characters"
    )
