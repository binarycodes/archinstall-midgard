#!/usr/bin/env bash

# Annotate manifest.yml with one-line pacman package descriptions.
# Usage: annotate_manifest.sh <manifest.yml>

set -euo pipefail
manifest="$1"

mapfile -t pkgs < <(yq -r '
    .pacstrap[],
    .post_chroot[],
    .packages[],
    .aur_packages[],
    .aur_helpers[]
' "$manifest" | sort -u)

# name<tab>description table from pacman's local dbs.
descs=$(mktemp); trap 'rm -f "$descs"' EXIT
{
    LC_ALL=C pacman -Si "${pkgs[@]}" 2>/dev/null || true
    LC_ALL=C pacman -Qi "${pkgs[@]}" 2>/dev/null || true
} | awk '
    /^Name *:/        { sub(/^Name *: */, ""); name = $0; next }
    /^Description *:/ {
        sub(/^Description *: */, "")
        sub(/\.$/, "")
        if (name && !(name in seen)) { print name "\t" $0; seen[name] = 1 }
        name = ""
    }
' > "$descs"

# rewrite each "<indent>- pkg [# old]" with the looked-up description.
awk -i inplace -v descs="$descs" '
    BEGIN {
        while ((getline line < descs) > 0) {
            t = index(line, "\t")
            d[substr(line, 1, t - 1)] = substr(line, t + 1)
        }
    }
    match($0, /^[[:space:]]+- /) {
        prefix = substr($0, 1, RLENGTH)
        pkg = substr($0, RLENGTH + 1)
        sub(/[ \t]*#.*$/, "", pkg)
        sub(/[ \t]+$/, "", pkg)
        if (pkg in d) { print prefix pkg " # " d[pkg]; next }
    }
    { print }
' "$manifest"
