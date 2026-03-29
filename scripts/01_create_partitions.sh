#!/bin/bash

DISK=/dev/nvme0n1
EFI="${DISK}p1"
SWAP="${DISK}p2"
ROOT="${DISK}p3"

EFI_PARTITION_TYPE=ef00
SWAP_PARTITION_TYPE=8200
LINUX_PARTITION_TYPE=8300

sgdisk --zap-all "$DISK"

sgdisk -n 1:0:+1G -t 1:"$EFI_PARTITION_TYPE" "$DISK"
sgdisk -n 2:0:+32G -t 2:"$SWAP_PARTITION_TYPE" "$DISK"
sgdisk -n 3:0:0 -t 3:"$LINUX_PARTITION_TYPE" "$DISK"

mkfs.fat -F32 "$EFI"
mkswap "$SWAP"
mkfs.btrfs "$ROOT"

mount "$ROOT" /mnt
mount --mkdir "$EFI" /mnt/boot
swapon "$SWAP"
