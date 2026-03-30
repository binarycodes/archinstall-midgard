#!/bin/bash
set -e

SCRIPT_DIR="/root/archinstall-midgard/scripts"
source "$SCRIPT_DIR/config.sh"

echo "==> Creating partitions..."
"$SCRIPT_DIR"/01_create_partitions.sh

echo "==> Installing base system..."
"$SCRIPT_DIR"/02_pacstrap.sh

# copy repo into chroot at a location accessible to all users
cp -r /root/archinstall-midgard /mnt/tmp/archinstall-midgard

echo "==> Running post-chroot setup..."
arch-chroot /mnt /tmp/archinstall-midgard/scripts/03_post_chroot.sh

echo "==> Creating boot entries..."
arch-chroot /mnt /tmp/archinstall-midgard/scripts/04_create_boot_entries.sh

echo "==> Installing packages..."
arch-chroot /mnt runuser -u "$USERNAME" -- /tmp/archinstall-midgard/scripts/05_packages.sh

# clean up
rm -rf /mnt/tmp/archinstall-midgard

echo "==> Install complete. Reboot and enjoy."
