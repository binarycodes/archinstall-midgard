#!/bin/bash
set -euo pipefail

SCRIPT_DIR="/root/archinstall-midgard/scripts"
# shellcheck source-path=SCRIPTDIR
source "$SCRIPT_DIR/config.sh"

echo "==> Creating partitions..."
"$SCRIPT_DIR"/01_create_partitions.sh

echo "==> Installing base system..."
"$SCRIPT_DIR"/02_pacstrap.sh

# copy repo into chroot at a location accessible to all users
# /tmp is avoided because arch-chroot mounts a tmpfs over it
cp -r /root/archinstall-midgard /mnt/opt/archinstall-midgard

echo "==> Running post-chroot setup..."
arch-chroot /mnt /opt/archinstall-midgard/scripts/03_post_chroot.sh

echo "==> Creating boot entries..."
arch-chroot /mnt /opt/archinstall-midgard/scripts/04_create_boot_entries.sh

echo "==> Installing packages..."
arch-chroot /mnt runuser -u "$USERNAME" -- /opt/archinstall-midgard/scripts/05_packages.sh

# clean up
rm -rf /mnt/opt/archinstall-midgard

echo "==> Install complete. Reboot and enjoy."
