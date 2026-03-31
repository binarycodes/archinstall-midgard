# archinstall-midgard

Custom Arch Linux installation scripts for a ThinkPad setup. Uses EFISTUB (no bootloader), btrfs, and systemd-networkd with iwd for wifi.

## Structure

- `scripts/config.sh` -- system configuration variables (disk, username, locale, etc.)
- `scripts/install.sh` -- main installer that runs all steps in order
- `scripts/` -- installation and maintenance scripts, numbered by execution order
- `scripts/manifest.yml` -- single source of truth for all packages
- `config/` -- system config files mirroring the filesystem layout (copied to `/` during install)

## Usage

Boot from the Arch ISO and install prerequisites:

```bash
pacman -Sy git yq
git clone https://github.com/binarycodes/archinstall-midgard.git /root/archinstall-midgard
cd /root/archinstall-midgard
```

Edit `scripts/config.sh` to match your system, then run the installer:

```bash
bash scripts/install.sh
```

This will partition the disk, install the base system, chroot to configure and create boot entries, and install all packages. You will be prompted to set passwords for root and your user during the process.

## Maintenance

To install new packages or re-apply configs, run `05_packages.sh` again.

To find explicitly installed packages not tracked in `manifest.yml`:

```bash
bash /root/archinstall-midgard/scripts/cleanup_packages.sh
```

## Configuration

Edit `scripts/config.sh` and `scripts/manifest.yml` to match your system before running. System config files live in `config/` and are copied to `/` during install and after package installs.
