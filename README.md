# archinstall-midgard

Custom Arch Linux installation. Installation is based on the manifest, the hardware that the installer detects, and the profile chosen at install.

## Structure

- `manifest.yml` -- the shared base every machine gets: system settings (username, locale, etc.), packages, services, gsettings and git repos
- `profiles/` -- one `<name>.yml` per profile, describing what a machine is used for
- `features/` -- one `<feature>.yml` per hardware feature, listing what that feature installs
- `installer/` -- the installer and maintenance tool, a Python package run with `uv`
- `config/` -- system config files mirroring the filesystem layout (copied to `/` during install)
- `dotfiles/` -- user dotfiles, stowed into `$HOME` on every machine

## Profiles

Each machine uses one profile, chosen at install with `--profile`. A profile uses the same sections as `manifest.yml`. Every section is optional, so an empty profile is valid.

A profile can extend other profiles, given as a single name or a list:

```yaml
extends: [workstation]
packages:
  - steam
```

The installer saves the profile on the new system in `/etc/installer/profile`.

>[Note] A profile cannot be changed later


## Hardware features

The installer detects these hardware features:

- `battery`
- `backlight`
- `kbd_backlight`
- `touchpad`
- `lid`
- `wifi`
- `bluetooth`
- `gpu_intel`
- `gpu_amd`

## Usage

Boot from the Arch ISO and install prerequisites:

```bash
pacman -Sy git uv
git clone https://github.com/binarycodes/archinstall-midgard.git /root/archinstall-midgard
cd /root/archinstall-midgard
```

Edit the settings at the top of `manifest.yml` if needed, then run the installer as root:

```bash
uv run installer install --hostname <name> --profile <profile>
```

The profile is the name of a file in `profiles/`.

The installer first checks the hostname, the profile and its merged manifest, and that the machine is booted in UEFI mode and online. It then shows the hostname, the profile with its chain and the detected features, lists the disks, and asks which one to install to. For the chosen disk it shows the current contents and the new layout, and erases the disk once you confirm by typing its name. After that it partitions the disk, installs the base system, saves the profile, and copies the repository into the new system. From a chroot it then configures the system, creates boot entries, installs all packages, clones your projects and stows the dotfiles. You will be asked to set passwords for root and your user along the way.

The disk is always chosen interactively during install. To try the selection without changing anything, run `uv run installer check -d`.

## Maintenance

After the first boot the repository lives in `~/projects/archinstall-midgard`. Run these as your user:

```bash
cd ~/projects/archinstall-midgard
uv run installer packages   # install new packages, re-apply configs, enable services
uv run installer daily      # packages, then clone missing projects and re-stow dotfiles
uv run installer cleanup    # list explicitly installed packages missing from this machine's manifest and offer to remove them
uv run installer annotate   # refresh the package description comments in the manifest, profiles and feature files
uv run installer validate   # check the manifest, profiles and feature files for mistakes
```

`validate` checks each file on its own, then the merged result of every profile with all feature files applied. Use `--profile <name>` to check a single profile, and `-p` to also look up every package in the repos and the AUR.

`check` prints what the installer detects. It works anywhere, including on the live ISO:

```bash
uv run installer check -u            # microcode package for this CPU
uv run installer check -r            # RAM in GiB
uv run installer check -s            # swap size for that RAM
uv run installer check -f            # every hardware feature, detected or not
uv run installer check -d            # dry run of the install's disk selection
uv run installer check -c <profile>  # the chain a profile resolves to
```

`uv run installer --help` lists every command, including the individual install steps.

## Development

```bash
uv sync
uv run pytest
uv run ruff check
```
