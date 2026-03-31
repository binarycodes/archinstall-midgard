#!/bin/bash
set -euo pipefail
# shellcheck source-path=SCRIPTDIR
source "$(dirname "$0")/config.sh"

configure_time() {
    ln -sf /usr/share/zoneinfo/"$TIMEZONE" /etc/localtime
    hwclock --systohc
}

configure_locale() {
    sed -i -e "s/#${LOCALE}/${LOCALE}/" /etc/locale.gen
    locale-gen
    echo "LANG=${LOCALE}" > /etc/locale.conf
    echo "KEYMAP=${KEYMAP}" > /etc/vconsole.conf
}

configure_system() {
    echo "$SYSTEM_HOSTNAME" > /etc/hostname
}

install_packages() {
    local packages_file
    packages_file="$(dirname "$0")/manifest.yml"
    local packages
    packages=$(yq -r '.post_chroot[]' "$packages_file")
    # shellcheck disable=SC2086
    pacman --noconfirm -S $packages
    mkinitcpio -P
}

enable_services() {
    systemctl enable systemd-networkd
    systemctl enable systemd-resolved
    systemctl enable iwd
    systemctl enable sshd
}

create_user() {
    echo "set password for root"
    passwd

    useradd -m -G wheel -s /usr/bin/zsh "$USERNAME"
    echo "set password for - $USERNAME"
    passwd "$USERNAME"
}

copy_configs() {
    local config_dir
    config_dir="$(dirname "$0")/../config"
    rsync -av --no-owner --no-group "$config_dir"/ /
}

copy_configs
configure_time
configure_locale
configure_system
install_packages
enable_services
create_user
