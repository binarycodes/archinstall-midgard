#!/bin/bash

VARS_FILE="$(dirname "$0")/manifest.yml"

PACKAGE_SECTIONS=(
    "applications"
    "aur_helpers"
    "aur_packages"
    "basic_packages"
    "dev_packages"
    "essential_drivers"
    "fonts"
    "language_servers"
    "pacstrap"
    "post_chroot"
    "wayland"
)

managed_packages() {
    {
        for section in "${PACKAGE_SECTIONS[@]}"; do
            yq -r ".${section}[]" "$VARS_FILE"
        done;

        yq -r '.url_packages[].name' "$VARS_FILE";
    } | sort -u
}

orphaned=$(comm -23 <(pacman -Qqe | sort) <(managed_packages))

if [ -z "$orphaned" ]; then
    echo "No orphaned packages found."
    exit 0
fi

echo "Explicitly installed packages not in manifest.yml:"
echo ""
echo "$orphaned"
echo ""
read -rp "Remove these packages? [y/N] " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # shellcheck disable=SC2086
    sudo pacman -Rcns $orphaned
fi
