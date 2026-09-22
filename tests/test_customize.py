from installer import customize


def test_gsettings_command_wraps_in_private_bus_only_when_asked():
    plain = customize.gsettings_command("s", "k", "v")
    assert plain == ("gsettings", "set", "s", "k", "v")
    assert customize.gsettings_command("s", "k", "v", private_bus=True) == (
        "dbus-run-session",
        "--",
        *plain,
    )


def test_customize_without_session_bus_uses_private_bus_and_runtime_dir(monkeypatch):
    calls = []
    monkeypatch.setattr(customize, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/0")

    customize.customize()

    assert len(calls) == len(customize.GSETTINGS)
    for args, kwargs in calls:
        assert args[:2] == ("dbus-run-session", "--")
        assert kwargs["env"]["XDG_RUNTIME_DIR"] != "/run/user/0"


def test_customize_with_session_bus_runs_gsettings_directly(monkeypatch):
    calls = []
    monkeypatch.setattr(customize, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")

    customize.customize()

    assert [args[0] for args, _ in calls] == ["gsettings"] * len(customize.GSETTINGS)
    assert all("env" not in kwargs for _, kwargs in calls)
