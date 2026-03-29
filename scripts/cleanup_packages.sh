#!/bin/bash

VARS_FILE="$(dirname "$0")/packages.yml"

PACKAGE_SECTIONS=(
    "pacstrap"
    "post_chroot"
    "package_dependencies"
    "basic_packages"
    "essential_drivers"
    "dev_packages"
    "fonts"
    "applications"
    "window_managers"
    "aur_packages"
)

managed_packages() {
    for section in "${PACKAGE_SECTIONS[@]}"; do
        yq -r ".${section}[]" "$VARS_FILE"
    done | sort -u
}

orphaned=$(comm -23 <(pacman -Qqe | sort) <(managed_packages))

if [ -z "$orphaned" ]; then
    echo "No orphaned packages found."
    exit 0
fi

echo "Explicitly installed packages not in packages.yml:"
echo ""
echo "$orphaned"
echo ""
read -p "Remove these packages? [y/N] " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    sudo pacman -Rns $orphaned
fi
