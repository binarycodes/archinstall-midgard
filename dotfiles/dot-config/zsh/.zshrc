# load modules
zmodload zsh/complist
autoload -Uz compinit && compinit -d ${XDG_CACHE_HOME}/zcompdump
autoload -Uz colors && colors

# cmp opts
zstyle ':completion::complete:*' cache-path ${XDG_CACHE_HOME}/zcompcache
zstyle ':completion:*' menu select # tab opens cmp menu
zstyle ':completion:*' special-dirs false # force . and .. to not show in cmp menu
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS} ma=0\;33 # colorize cmp menu
zstyle ':completion:*' file-list true # more detailed list
zstyle ':completion:*' squeeze-slashes false # explicit disable to allow /*/ expansion

# main opts
# on exit, history appends rather than overwrites; history is appended as soon as cmds executed; history shared across sessions
setopt append_history inc_append_history share_history # better history
setopt auto_menu menu_complete # autocmp first menu match
setopt autocd # type a dir to cd
setopt auto_param_slash # when a dir is completed, add a / instead of a trailing space
setopt no_case_glob no_case_match # make cmp case insensitive
setopt globdots # include dotfiles
setopt extended_glob # match ~ # ^
setopt interactive_comments # allow comments in shell
unsetopt prompt_sp # don't autoclean blanklines
stty stop undef # disable accidental ctrl s

# history opts
HISTSIZE=1000000
SAVEHIST=1000000
HISTFILE="$XDG_CACHE_HOME/zsh_history" # move histfile to cache
HISTCONTROL=ignoreboth # consecutive duplicates & commands starting with space are not saved

# binds
bindkey -e
bindkey "^[[A" history-beginning-search-backward
bindkey "^[[B" history-beginning-search-forward

# Copy (like M-w in Emacs)
function zle-copy-region-to-clipboard() {
  zle copy-region-as-kill
  print -rn -- "$CUTBUFFER" | wl-copy
}
zle -N zle-copy-region-to-clipboard
bindkey '^[w' zle-copy-region-to-clipboard

# Cut (like C-w in Emacs)
function zle-kill-region-to-clipboard() {
  zle kill-region
  print -rn -- "$CUTBUFFER" | wl-copy
}
zle -N zle-kill-region-to-clipboard
bindkey '^w' zle-kill-region-to-clipboard

# Paste (like C-y in Emacs)
function paste-from-clipboard() {
  LBUFFER+=$(wl-paste)
}
zle -N paste-from-clipboard
bindkey '^y' paste-from-clipboard


# set up prompt
NEWLINE=$'\n'
PROMPT="%K{#2E3440}%F{#E5E9F0}$(date +%0H:%M) %K{#3b4252}%F{#ECEFF4} %n %K{#4c566a} %~ %f%k ❯ "

# autosuggestions
# requires zsh-autosuggestions
source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
