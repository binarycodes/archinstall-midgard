#!/bin/bash

PACKAGES_FILE="$(dirname "$0")/packages.yml"
PACKAGES=$(sed -n '/^pacstrap:/,/^[^ ]/p' "$PACKAGES_FILE" | grep '^\s*-' | sed 's/\s*-\s*//')

mkdir -p /mnt/etc/
echo "KEYMAP=us" >> /mnt/etc/vconsole.conf

pacstrap -K /mnt $PACKAGES

genfstab -U /mnt >> /mnt/etc/fstab
cp -R /root/archinstall-midgard /mnt/root/
