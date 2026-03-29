#!/bin/bash

mkdir -p /mnt/etc/
echo "KEYMAP=us" >> /mnt/etc/vconsole.conf

pacstrap -K /mnt base base-devel linux linux-firmware linux-headers intel-ucode btrfs-progs

genfstab -U /mnt >> /mnt/etc/fstab
cp -R /root/archinstall-midgard /mnt/root/
