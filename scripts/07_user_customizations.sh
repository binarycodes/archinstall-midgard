#!/bin/bash
set -euo pipefail

if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run this script as root."
    exit 1
fi

gsettings set org.gnome.desktop.interface color-scheme prefer-dark
gsettings set org.gnome.desktop.interface gtk-theme Adwaita-dark
gsettings set org.gnome.desktop.interface icon-theme Papirus
gsettings set org.gnome.desktop.interface font-name "Roboto 12"
