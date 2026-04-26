#!/bin/bash

VARS_FILE="$(dirname "$0")/manifest.yml"

managed_packages() {
    yq -r '
        .pacstrap[],
        .post_chroot[],
        .packages[],
        .aur_packages[],
        .aur_helpers[],
        .url_packages[].name
    ' "$VARS_FILE" | sort -u
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
