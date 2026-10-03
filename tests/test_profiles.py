import pytest

from installer import profiles
from installer.profiles import ProfileError, chain


def test_profile_without_extends_is_its_own_chain():
    assert chain("a", {"a": {}}) == ["a"]


def test_single_extends_name():
    assert chain("a", {"a": {"extends": "b"}, "b": {}}) == ["b", "a"]


def test_multiple_extends_in_listed_order():
    loaded = {"a": {"extends": ["c", "b"]}, "b": {}, "c": {}}
    assert chain("a", loaded) == ["c", "b", "a"]


def test_nested_extends_resolve_depth_first():
    loaded = {"a": {"extends": ["b", "d"]}, "b": {"extends": ["c"]}, "c": {}, "d": {}}
    assert chain("a", loaded) == ["c", "b", "d", "a"]


def test_diamond_applies_shared_profile_once_at_first_position():
    loaded = {
        "a": {"extends": ["b", "c"]},
        "b": {"extends": ["d"]},
        "c": {"extends": ["d"]},
        "d": {},
    }
    assert chain("a", loaded) == ["d", "b", "c", "a"]


def test_cycle_is_spelled_out():
    loaded = {"a": {"extends": ["b"]}, "b": {"extends": ["a"]}}
    with pytest.raises(ProfileError, match="^extension cycle: a → b → a$"):
        chain("a", loaded)


def test_cycle_below_the_profile():
    loaded = {"a": {"extends": ["b"]}, "b": {"extends": ["c"]}, "c": {"extends": ["b"]}}
    with pytest.raises(ProfileError, match="^extension cycle: b → c → b$"):
        chain("a", loaded)


def test_profile_extending_itself_is_a_cycle():
    with pytest.raises(ProfileError, match="^extension cycle: a → a$"):
        chain("a", {"a": {"extends": "a"}})


def test_unknown_profile_lists_profiles():
    with pytest.raises(ProfileError, match=r"^unknown profile 'x'; profiles in profiles/: a, b$"):
        chain("x", {"b": {}, "a": {}})


def test_unknown_extends():
    with pytest.raises(ProfileError, match=r"^profile 'a' extends unknown profile 'x'; "):
        chain("a", {"a": {"extends": ["x"]}})


def test_listing_without_profiles():
    assert profiles.listing([]) == "no profiles in profiles/"


def test_describe():
    assert profiles.describe(["b", "a"]) == "base → b → a"


def test_body_drops_extends():
    assert profiles.body({"extends": ["b"], "keymap": "fi"}) == {"keymap": "fi"}


def test_empty_profile_file_loads_as_nothing(tmp_path):
    path = tmp_path / "p.yml"
    path.write_text("")
    assert profiles.load(path) == {}


def test_saved_profile_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(profiles, "write_file", lambda path, text: path.write_text(text))
    profiles.save("gaming", str(tmp_path))
    saved = tmp_path / "etc" / "installer" / "profile"
    assert saved.read_text() == "gaming\n"
