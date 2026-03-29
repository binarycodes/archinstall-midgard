#!/bin/bash

if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run this script as root."
    exit 1
fi

VARS_FILE="$(dirname "$0")/packages.yml"

parse_packages() {
    local section="$1"
    yq -r ".${section}[]" "$VARS_FILE"
}

install_packages() {
    local section="$1"
    local packages
    packages=$(parse_packages "$section")

    if [ -z "$packages" ]; then
        echo "No packages found for section: $section"
        return
    fi

    echo "Installing $section..."
    sudo pacman --noconfirm --needed -S $packages
}

install_url_packages() {
    local urls
    urls=$(parse_packages "url_packages")

    if [ -z "$urls" ]; then
        echo "No URL packages found"
        return
    fi

    echo "Installing URL packages..."
    sudo pacman --noconfirm --needed -U $urls
}

install_aur_packages() {
    local section="$1"
    local packages
    packages=$(parse_packages "$section")

    if [ -z "$packages" ]; then
        echo "No AUR packages found for section: $section"
        return
    fi

    echo "Installing AUR $section..."
    yay -S --answerclean None --answerdiff None --noconfirm --needed $packages
}

install_yay() {
    if command -v yay &>/dev/null; then
        echo "yay already installed, skipping..."
        return
    fi

    local tmpdir
    tmpdir=$(mktemp -d)
    git clone https://aur.archlinux.org/yay.git "$tmpdir/yay"
    cd "$tmpdir/yay"
    makepkg -si --noconfirm
    cd -
    rm -rf "$tmpdir"
}

enable_services() {
    local services
    services=$(parse_packages "services_to_enable")

    for service in $services; do
        echo "Enabling $service..."
        sudo systemctl enable --now "$service"
    done
}

sudo pacman -Syu --noconfirm

install_packages "package_dependencies"
install_packages "basic_packages"
install_packages "essential_drivers"
install_packages "dev_packages"
install_packages "fonts"
install_packages "applications"
install_packages "window_managers"

install_yay
install_aur_packages "aur_packages"
install_url_packages

enable_services
