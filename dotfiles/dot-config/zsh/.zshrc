# --- Paths for autoloading ---
fpath=(
  ~/.zsh/functions
  $fpath
)

# load modules
zmodload zsh/complist
autoload -Uz compinit && compinit -d ${XDG_CACHE_HOME}/zcompdump
autoload -Uz colors && colors
autoload -Uz edit-command-line

# load custom functions/widgets
autoload -Uz ${ZDOTDIR}/functions/*

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
HISTFILE="${XDG_CACHE_HOME}/zsh_history" # move histfile to cache

setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_SAVE_NO_DUPS
setopt HIST_EXPIRE_DUPS_FIRST

# set up prompt
NEWLINE=$'\n'
PROMPT="%K{#2E3440}%F{#E5E9F0}%D{%H:%M} %K{#3b4252}%F{#ECEFF4} %n %K{#4c566a} %~ %f%k ❯ "

# autosuggestions - but not in tty sessions
# requires zsh-autosuggestions
if [[ -n "$WAYLAND_DISPLAY" || -n "$DISPLAY" ]]; then
    source "${ZSH_AUTOSUGGESTIONS_PATH:-/usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh}"
fi

for file in "$ZDOTDIR"/{aliases,bindkeys}.zsh; do
    [[ -r "$file" ]] && source "$file"
done
