#!/bin/bash

DISK=/dev/nvme0n1
ROOT="${DISK}p3"
ROOT_UUID=$(blkid "$ROOT" -s UUID -o value)

efibootmgr -b1 -B

efibootmgr --create \
	--disk "$DISK" --part 1 \
	--label "Arch Linux" \
	--loader /vmlinuz-linux \
	--unicode "initrd=\intel-ucode.img initrd=\initramfs-linux.img root=UUID=$ROOT_UUID rw quiet loglevel=3"

efibootmgr -b2 -B

efibootmgr --create \
	--disk "$DISK" --part 1 \
	--label "Arch Linux LTS" \
	--loader /vmlinuz-linux-lts \
	--unicode "initrd=\intel-ucode.img initrd=\initramfs-linux-lts.img root=UUID=$ROOT_UUID rw quiet loglevel=3"
