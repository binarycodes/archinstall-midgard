#!/bin/bash
set -euo pipefail

# shellcheck source-path=SCRIPTDIR
source "$(dirname "$0")/config.sh"

MANIFEST_FILE="$(dirname "$0")/manifest.yml"
PROJECTS_DIR="$HOME/projects"

mkdir -p "$PROJECTS_DIR"

repos=$(yq -r '.git_repos[]' "$MANIFEST_FILE")

for repo in $repos; do
    name=$(basename "$repo" .git)
    if [ -d "$PROJECTS_DIR/$name" ]; then
        echo "Skipping $name (already exists)"
        continue
    fi
    echo "Cloning $repo..."
    git clone "$repo" "$PROJECTS_DIR/$name"
done

DOTFILES_DIR="$PROJECTS_DIR/$INSTALL_REPO/dotfiles"

if [ -d "$DOTFILES_DIR" ]; then
    echo "Running make in dotfiles..."
    make -C "$DOTFILES_DIR"
fi
