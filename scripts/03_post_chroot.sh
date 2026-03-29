#!/bin/bash

USERNAME="sujoy"
SYSTEM_HOSTNAME="midgard"
TIMEZONE="Europe/Helsinki"
LOCALE="en_US.UTF-8"
KEYMAP="us"

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
    echo "export SUDO_EDITOR=/usr/bin/vim" > /etc/profile.d/sudo_editor.sh
}

install_packages() {
    pacman --noconfirm -S efibootmgr openssh iwd sudo zsh ansible yq
    pacman --noconfirm -S linux-lts linux-lts-headers
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

    echo "%wheel         ALL = (root) NOPASSWD: ALL" > /etc/sudoers.d/01_nopasswd_wheel
}

configure_networking() {
    cat << EOF > /etc/iwd/main.conf
[General]
EnableNetworkConfiguration=false

[Network]
NameResolvingService=systemd
EOF

    cat << EOF > /etc/systemd/network/20-wired.network
[Match]
Name=en*

[Network]
DHCP=yes

[DHCPv4]
RouteMetric=100
EOF

    cat << EOF > /etc/systemd/network/25-wireless.network
[Match]
Name=wlan*

[Network]
DHCP=yes

[DHCPv4]
RouteMetric=600
EOF
}

configure_time
configure_locale
configure_system
install_packages
enable_services
create_user
configure_networking

echo "remember to create efi boot entries"
