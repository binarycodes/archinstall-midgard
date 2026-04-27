function zle-kill-region-to-clipboard() {
    zle kill-region
    print -rn -- "$CUTBUFFER" | wl-copy
}
