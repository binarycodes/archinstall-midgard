#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Creating partitions..."
"$SCRIPT_DIR"/01_create_partitions.sh

echo "==> Installing base system..."
"$SCRIPT_DIR"/02_pacstrap.sh

# copy scripts into chroot so they're accessible
cp -r "$SCRIPT_DIR" /mnt/install-scripts

echo "==> Running post-chroot setup..."
arch-chroot /mnt /install-scripts/03_post_chroot.sh

echo "==> Creating boot entries..."
arch-chroot /mnt /install-scripts/04_create_boot_entries.sh

# clean up
rm -rf /mnt/install-scripts

echo "==> Base install complete. Reboot and run 05_packages.sh as your user."
