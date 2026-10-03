import pytest

from installer import user_inputs
from installer.disk import DiskError
from installer.user_inputs import InputError, UserInputs, ask_password, collect


def answers(*values):
    """An ask() that returns each value in turn; an exception value is raised instead."""
    pending = list(values)
    asked = []

    def ask(question):
        asked.append(question)
        value = pending.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    ask.asked = asked
    return ask


def test_password_typed_twice():
    ask = answers("s3cret", "s3cret")
    assert ask_password("u", ask) == "s3cret"
    assert ask.asked == ["Password for [bold]u[/]: ", "Repeat the password for [bold]u[/]: "]


def test_password_asked_again_until_both_match():
    assert ask_password("u", answers("a", "b", "c", "c")) == "c"


def test_empty_password_is_asked_again():
    assert ask_password("u", answers("", "x", "x")) == "x"


def test_end_of_input_aborts():
    with pytest.raises(InputError, match="no password given for root"):
        ask_password("root", answers(EOFError()))


def test_collect_asks_for_the_disk_then_root_then_the_user(monkeypatch):
    order = []
    monkeypatch.setattr(user_inputs, "select_disk", lambda swap: order.append("disk") or "sda")
    monkeypatch.setattr(
        user_inputs, "ask_password", lambda account: order.append(account) or f"{account}-pw"
    )
    assert collect(17, "u") == UserInputs("sda", {"root": "root-pw", "u": "u-pw"})
    assert order == ["disk", "root", "u"]


def test_collect_stops_when_the_disk_is_not_confirmed(monkeypatch):
    def abort(swap):
        raise DiskError("not confirmed")

    monkeypatch.setattr(user_inputs, "select_disk", abort)
    monkeypatch.setattr(user_inputs, "ask_password", lambda account: pytest.fail("asked"))
    with pytest.raises(InputError, match="not confirmed"):
        collect(17, "u")
