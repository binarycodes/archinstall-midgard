#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"

echo "==> Updating packages..."
"$SCRIPT_DIR"/05_packages.sh

echo "==> Setting up user projects..."
"$SCRIPT_DIR"/06_setup_user_projects.sh
