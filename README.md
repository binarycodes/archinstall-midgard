# archinstall-midgard

Custom Arch Linux installation scripts for a ThinkPad setup. Uses EFISTUB (no bootloader), btrfs, and systemd-networkd with iwd for wifi.

## Structure

- `manifest.yml` -- single source of truth: system settings (disk, username, locale, etc.) and all packages
- `installer/` -- the installer and maintenance tool, a Python package run with `uv`
- `config/` -- system config files mirroring the filesystem layout (copied to `/` during install)
- `dotfiles/` -- user dotfiles, stowed into `$HOME` after install
- `scripts/` -- the original shell scripts, kept for reference

## Usage

Boot from the Arch ISO and install prerequisites:

```bash
pacman -Sy git uv
git clone https://github.com/binarycodes/archinstall-midgard.git /root/archinstall-midgard
cd /root/archinstall-midgard
```

Edit the settings at the top of `manifest.yml` to match your system, then run the installer as root:

```bash
uv run installer install
```

This will partition the disk, install the base system, copy the repository into the new system, and from a chroot configure the system, create boot entries, install all packages, clone your projects and stow the dotfiles. You will be prompted to set passwords for root and your user during the process.

The `disk` setting takes the whole device, for example `/dev/nvme0n1` or `/dev/sda`; partition names are derived from it.

## Maintenance

After the first boot the repository lives in `~/projects/archinstall-midgard`. Run these as your user:

```bash
cd ~/projects/archinstall-midgard
uv run installer packages   # install new packages, re-apply configs, enable services
uv run installer daily      # packages, then clone missing projects and re-stow dotfiles
uv run installer cleanup    # show explicitly installed packages not in the manifest and offer to remove them
uv run installer annotate   # refresh the package description comments in manifest.yml
```

`uv run installer --help` lists every command, including the individual install steps.

## Development

```bash
uv sync
uv run pytest
uv run ruff check
```
