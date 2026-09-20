from installer.shell import run

GSETTINGS = (
    ("org.gnome.desktop.interface", "color-scheme", "prefer-dark"),
    ("org.gnome.desktop.interface", "gtk-theme", "Adwaita-dark"),
    ("org.gnome.desktop.interface", "icon-theme", "Papirus"),
    ("org.gnome.desktop.interface", "font-name", "Roboto 12"),
)


def customize() -> None:
    for schema, key, value in GSETTINGS:
        run("gsettings", "set", schema, key, value)
