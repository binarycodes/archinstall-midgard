# archinstall-midgard

Custom Arch Linux installation scripts for a ThinkPad setup. Uses EFISTUB (no bootloader), btrfs, systemd-networkd with iwd for wifi, and KDE Plasma.

## Usage

Boot from the Arch ISO, clone this repo, then run the scripts in order:

```bash
# 1. Partition, format, and mount the disk
bash scripts/01_create_partitions.sh

# 2. Install base system via pacstrap
bash scripts/02_pacstrap.sh

# 3. Chroot and configure the system
arch-chroot /mnt bash /root/archinstall-midgard/scripts/03_post_chroot.sh

# 4. Create UEFI boot entries (run inside chroot)
arch-chroot /mnt bash /root/archinstall-midgard/scripts/04_create_boot_entries.sh

# 5. Reboot, then install packages and enable services
bash scripts/05_packages.sh
```

Edit the variables at the top of each script and `scripts/packages.yml` to match your system before running.
