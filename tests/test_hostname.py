import pytest

from installer import hostname


@pytest.mark.parametrize("name", ["midgard", "a", "x1", "my-laptop", "1984", "a" * 63])
def test_valid(name):
    assert hostname.problem(name) is None


@pytest.mark.parametrize(
    "name",
    ["", "Midgard", "-midgard", "midgard-", "mid_gard", "midgard.local", "mid gard", "a" * 64],
)
def test_invalid(name):
    assert hostname.problem(name).startswith(f"hostname {name!r} is not valid")
