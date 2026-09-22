from installer import customize, manifest, paths

DATA = {
    "gsettings": {
        "org.gnome.desktop.interface": {"color-scheme": "prefer-dark", "font-name": "Roboto 12"},
        "org.gnome.desktop.peripherals.touchpad": {"tap-to-click": True},
    }
}


def test_gsettings_entries_flatten_schemas_and_lowercase_bools():
    assert customize.gsettings_entries(DATA) == [
        ("org.gnome.desktop.interface", "color-scheme", "prefer-dark"),
        ("org.gnome.desktop.interface", "font-name", "Roboto 12"),
        ("org.gnome.desktop.peripherals.touchpad", "tap-to-click", "true"),
    ]


def test_gsettings_entries_missing_or_empty_section():
    assert customize.gsettings_entries({}) == []
    assert customize.gsettings_entries({"gsettings": None}) == []
    assert customize.gsettings_entries({"gsettings": {"org.x": None}}) == []


def test_repo_manifest_has_gsettings():
    assert customize.gsettings_entries(manifest.load(paths.MANIFEST))


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

    customize.customize(DATA)

    assert len(calls) == 3
    for args, kwargs in calls:
        assert args[:2] == ("dbus-run-session", "--")
        assert kwargs["env"]["XDG_RUNTIME_DIR"] != "/run/user/0"


def test_customize_with_session_bus_runs_gsettings_directly(monkeypatch):
    calls = []
    monkeypatch.setattr(customize, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")

    customize.customize(DATA)

    assert [args[0] for args, _ in calls] == ["gsettings"] * 3
    assert all("env" not in kwargs for _, kwargs in calls)
