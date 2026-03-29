#!/bin/bash

DISK=/dev/nvme0n1
ROOT="${DISK}p3"
ROOT_UUID=$(blkid "$ROOT" -s UUID -o value)

# remove old OS boot entries, keep firmware entries (PXE, CD-ROM, USB, etc.)
KEEP_PATTERN="PXE|CD|DVD|USB|NIC|IPv[46]|Network|Lenovo|ATA"
for entry in $(efibootmgr | grep '^Boot[0-9]' | grep -ivE "$KEEP_PATTERN" | sed 's/Boot\([0-9A-F]*\).*/\1/'); do
    echo "Removing boot entry: $entry"
    efibootmgr -b "$entry" -B
done

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
