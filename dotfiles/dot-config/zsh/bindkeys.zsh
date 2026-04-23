bindkey -e
bindkey "^[[A" history-beginning-search-backward # up arrow
bindkey "^[[B" history-beginning-search-forward # down arrow
bindkey "^[[Z" magic-space # shift-tab

# Copy (like M-w in Emacs)
zle -N zle-copy-region-to-clipboard
bindkey '^[w' zle-copy-region-to-clipboard

# Cut (like C-w in Emacs)
zle -N zle-kill-region-to-clipboard
bindkey '^w' zle-kill-region-to-clipboard

# Paste (like C-y in Emacs)
zle -N paste-from-clipboard
bindkey '^y' paste-from-clipboard

# Open editor to edit command line (C-x C-e)
zle -N edit-command-line-editor
bindkey '^X^E' edit-command-line-editor
