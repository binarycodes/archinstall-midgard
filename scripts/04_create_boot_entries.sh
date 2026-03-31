#!/bin/bash
set -euo pipefail
# shellcheck source-path=SCRIPTDIR
source "$(dirname "$0")/config.sh"

ROOT_UUID=$(blkid "$ROOT" -s UUID -o value)

# delete existing Arch Linux boot entries
while read -r bootnum; do
	efibootmgr --delete-bootnum --bootnum "$bootnum"
done < <(efibootmgr | grep "Arch Linux" | sed 's/Boot\([0-9A-F]*\).*/\1/')

efibootmgr --create \
	--disk "$DISK" --part 1 \
	--label "Arch Linux" \
	--loader /vmlinuz-linux \
	--unicode "initrd=\intel-ucode.img initrd=\initramfs-linux.img root=UUID=$ROOT_UUID rw quiet loglevel=3"

efibootmgr --create \
	--disk "$DISK" --part 1 \
	--label "Arch Linux LTS" \
	--loader /vmlinuz-linux-lts \
	--unicode "initrd=\intel-ucode.img initrd=\initramfs-linux-lts.img root=UUID=$ROOT_UUID rw quiet loglevel=3"

# set boot order with Arch entries first, keep existing entries after
ARCH_REGULAR=$(efibootmgr | grep "Arch Linux" | grep -v "LTS" | sed 's/Boot\([0-9A-F]*\).*/\1/')
ARCH_LTS=$(efibootmgr | grep "Arch Linux LTS" | sed 's/Boot\([0-9A-F]*\).*/\1/')
ARCH_ENTRIES="${ARCH_REGULAR},${ARCH_LTS}"
OTHER_ENTRIES=$(efibootmgr | grep '^Boot[0-9]' | grep -v "Arch Linux" | sed 's/Boot\([0-9A-F]*\).*/\1/' | tr '\n' ',' | sed 's/,$//')
efibootmgr -o "${ARCH_ENTRIES},${OTHER_ENTRIES}"

# verify boot files exist
BOOT_FILES=(
    /boot/vmlinuz-linux
    /boot/vmlinuz-linux-lts
    /boot/initramfs-linux.img
    /boot/initramfs-linux-lts.img
    /boot/intel-ucode.img
)

for file in "${BOOT_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "WARNING: $file not found"
    fi
done

# verify boot entries
if ! efibootmgr | grep -q "Arch Linux"; then
    echo "WARNING: No Arch Linux boot entries found"
else
    echo "Boot entries:"
    efibootmgr
fi
