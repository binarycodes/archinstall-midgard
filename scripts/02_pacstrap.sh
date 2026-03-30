#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/config.sh"

PACKAGES_FILE="$(dirname "$0")/packages.yml"
PACKAGES=$(yq -r '.pacstrap[]' "$PACKAGES_FILE")

mkdir -p /mnt/etc/
echo "KEYMAP=$KEYMAP" > /mnt/etc/vconsole.conf

pacstrap -K /mnt $PACKAGES

genfstab -U /mnt >> /mnt/etc/fstab
