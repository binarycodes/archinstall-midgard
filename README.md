# archinstall-midgard

Custom Arch Linux installation scripts for a ThinkPad setup. Uses EFISTUB (no bootloader), btrfs, and systemd-networkd with iwd for wifi.

## Structure

- `scripts/` -- installation and maintenance scripts, numbered by execution order
- `scripts/packages.yml` -- single source of truth for all packages
- `config/` -- system config files mirroring the filesystem layout (copied to `/` during install)

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

# 5. Reboot, log in as your user, then install packages and enable services
bash scripts/05_packages.sh
```

## Maintenance

To find explicitly installed packages not tracked in `packages.yml`:

```bash
bash scripts/cleanup_packages.sh
```

## Configuration

Edit the variables at the top of each script and `scripts/packages.yml` to match your system before running. System config files live in `config/` and are copied to `/` during the post-chroot step.
