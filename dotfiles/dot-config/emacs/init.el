;;; init.el -*- lexical-binding: t; -*-

(defun bc-emacs-cache-dir (subpath)
  "Return a full path to a subdirectory under XDG_CACHE_HOME."
  (file-name-concat (getenv "XDG_CACHE_HOME") "emacs" subpath))

;; create relevant directories used later in config
(make-directory (bc-emacs-cache-dir "history") t)
(make-directory (bc-emacs-cache-dir "backup") t)
(make-directory (bc-emacs-cache-dir "packages") t)

(setopt package-user-dir (bc-emacs-cache-dir "packages")
	    package-gnupghome-dir (bc-emacs-cache-dir "gnupg")
	    )

;; elpa servers
(setopt package-archives '(("melpa" . "https://melpa.org/packages/")
                           ("org" . "https://orgmode.org/elpa/")
                           ("elpa" . "https://elpa.gnu.org/packages/")))

(setopt gnutls-algorithm-priority "NORMAL:+VERS-TLS1.3")

;; Initialize the package system early
(package-initialize)

;; Set eln-cache dir
(when (boundp 'native-comp-eln-load-path)
  (startup-redirect-eln-cache (bc-emacs-cache-dir "eln-cache")))

(setopt use-package-always-ensure t)

(setopt custom-file (locate-user-emacs-file (bc-emacs-cache-dir "custom-vars.el")))
(load custom-file 'noerror 'nomessage)

;; save history from previous sessions
(setopt savehist-file (bc-emacs-cache-dir "history/savehist"))
(savehist-mode 1)

;; clipboard history that survives restarts
(setopt savehist-additional-variables
  	    '(search-ring regexp-search-ring kill-ring))

;; the kill ring can accumulate text properties (fonts, overlays, etc.) that bloat the savehist file, strip them before saving
(add-hook 'savehist-save-hook
          (lambda ()
            (setq kill-ring
                  (mapcar #'substring-no-properties
                          (cl-remove-if-not #'stringp kill-ring)))))

;; Set the directory for auto-save files
(setopt auto-save-list-file-prefix
        (file-name-concat (bc-emacs-cache-dir "auto-save-list") ".saves-"))

;; backup settings
(setopt backup-by-copying t
        backup-directory-alist `(("." . ,(bc-emacs-cache-dir "backup")))
        create-lockfiles nil
        delete-old-versions t
        kept-new-versions 4
        kept-old-versions 2
        version-control t
        )

(setopt transient-levels-file (bc-emacs-cache-dir "transient/levels.el")
        transient-values-file (bc-emacs-cache-dir "transient/values.el")
        transient-history-file (bc-emacs-cache-dir "transient/history.el"))

;; clean startup
(setopt
 blink-cursor-interval 0.7
 confirm-kill-emacs 'yes-or-no-p
 inhibit-startup-echo-area-message ""
 inhibit-startup-message t
 initial-scratch-message ""
 use-dialog-box nil
 use-short-answers t
 visible-bell t ; flash the screen, when moving out of bounds, ex, pressing up when already at the first line.
 )

;; disable fancy gui stuffs, menu et. all and other ui configs
(menu-bar-mode -1)   ; disable the menu bar
(mouse-avoidance-mode 'banish) ; banish the cursor as soon as i am typing
(scroll-bar-mode -1) ; disable visible scrollbar
(tool-bar-mode -1)   ; disable the toolbar
(tooltip-mode -1)    ; disable tooltips

;; theme
(load-theme 'modus-vivendi t)

;; fonts/faces
(set-face-attribute 'default nil :font "JetBrains Mono" :height 120)
(set-face-attribute 'fixed-pitch nil :font "JetBrains Mono" :height 120)
(set-face-attribute 'variable-pitch nil :font "Roboto" :height 120 :weight 'regular)

(fringe-mode '(10 . 0)) ; give some space for the symbols (only of the left)
(column-number-mode 't) ; show column number in the modeline

(global-display-line-numbers-mode 0)

;; show line numbers in specific modes
(use-package display-line-numbers
  :defer
  :custom
  (display-line-numbers-width-start t)
  :hook
  ((prog-mode . display-line-numbers-mode)
   (TeX-mode . display-line-numbers-mode)
   (markdown-mode . display-line-numbers-mode)
   (conf-mode . display-line-numbers-mode)))

;; coding system - utf8 everywhere
(prefer-coding-system 'utf-8)
(set-default-coding-systems 'utf-8)
(set-terminal-coding-system 'utf-8)
(set-keyboard-coding-system 'utf-8)

(setq-default
 indent-tabs-mode nil
 tab-width 4
 tab-stop-list (number-sequence 4 180 4))

;; auto revert to on disk changes
(global-auto-revert-mode t)

;; require new line at the end
(setopt require-final-newline t)

(add-hook 'before-save-hook 'delete-trailing-whitespace)

(electric-pair-mode t)

;; not sure why these are disabled by default; enable case toggle
(put 'upcase-region 'disabled nil)
(put 'downcase-region 'disabled nil)

;; assume left-to-right text everywhere and skip the bidirectional parenthesis algorithm
(setq-default bidi-display-reordering 'left-to-right
              bidi-paragraph-direction 'left-to-right)
(setopt bidi-inhibit-bpa t)

;; The `wgrep' packages lets us edit the results of a grep search
;; while inside a `grep-mode' buffer.  All we need is to toggle the
;; editable mode, make the changes, and then type C-c C-c to confirm
;; or C-c C-k to abort.
(use-package wgrep
  :ensure t
  :bind ( :map grep-mode-map
          ("e" . wgrep-change-to-wgrep-mode)
          ("C-x C-q" . wgrep-change-to-wgrep-mode)
          ("C-c C-c" . wgrep-finish-edit)))

(setopt help-window-select t)

(use-package ace-window
  :ensure t
  :config (ace-window-display-mode t)
  :custom
  (aw-scope 'frame)
  (aw-minibuffer-flag t)
  )

(defvar-keymap bc/windmove-keymap
  :repeat t
  "h" #'windmove-left
  "j" #'windmove-up
  "k" #'windmove-down
  "l" #'windmove-right
  )

(keymap-global-set "C-c w" bc/windmove-keymap)

;; The `vertico' package applies a vertical layout to the minibuffer.
;; It also pops up the minibuffer eagerly so we can see the available
;; options without further interactions.  This package is very fast
;; and "just works", though it also is highly customisable in case we
;; need to modify its behaviour.
(use-package vertico
  :ensure t
  :config
  (setopt vertico-cycle t
          vertico-resize nil)
  (vertico-mode t))

;; The `marginalia' package provides helpful annotations next to
;; completion candidates in the minibuffer.  The information on
;; display depends on the type of content.  If it is about files, it
;; shows file permissions and the last modified date.  If it is a
;; buffer, it shows the buffer's size, major mode, and the like.
(use-package marginalia
  :ensure t
  :config
  (marginalia-mode t))

;; The `consult' package provides lots of commands that are enhanced
;; variants of basic, built-in functionality.  One of the headline
;; features of `consult' is its preview facility, where it shows in
;; another Emacs window the context of what is currently matched in
;; the minibuffer.  Here I define key bindings for some commands you
;; may find useful.  The mnemonic for their prefix is "alternative
;; search" (as opposed to the basic C-s or C-r keys).
(use-package consult
  :ensure t
  :bind (("M-s M-g" . consult-grep) ; a recursive grep
         ("M-s M-f" . consult-find) ; search for files names recursively
         ("M-s M-o" . consult-outline) ; search through the outline (headings) of the file
         ("M-s M-l" . consult-line) ; search the current buffer
         ("M-s M-b" . consult-buffer) ; switch to another buffer, or bookmarked file, or recently opened file.
         ("M-s M-r" . consult-recent-file) ; search through recently opened files
         ))

;; The `orderless' package lets the minibuffer use an out-of-order
;; pattern matching algorithm.  It matches space-separated words or
;; regular expressions in any order.  In its simplest form, something
;; like "ins pac" matches `package-menu-mark-install' as well as
;; `package-install'.  This is a powerful tool because we no longer
;; need to remember exactly how something is named.
(use-package orderless
  :ensure t
  :custom
  (orderless-matching-styles '(orderless-literal orderless-prefixes))
  (completion-ignore-case t)
  :config
  (set-face-attribute 'orderless-match-face-0 nil
                      :foreground "#d70000")
  (set-face-attribute 'orderless-match-face-1 nil
                      :foreground "#005fd7")
  (set-face-attribute 'orderless-match-face-2 nil
                      :foreground "#007f3a")
  (set-face-attribute 'orderless-match-face-3 nil
                      :foreground "#d700d7")

  (setopt completion-styles '(orderless partial-completion basic)
          completion-category-overrides '(
                                          (file (styles orderless partial-completion basic))
                                          (buffer (styles orderless partial-completion basic))
                                          )
          )
  )

;; The `embark-consult' package is glue code to tie together `embark'
;; and `consult'.
(use-package embark-consult
  :ensure t)

;; The `embark' package lets you target the thing or context at point
;; and select an action to perform on it.  Use the `embark-act'
;; command while over something to find relevant commands.
;;
;; When inside the minibuffer, `embark' can collect/export the
;; contents to a fully fledged Emacs buffer.  The `embark-collect'
;; command retains the original behaviour of the minibuffer, meaning
;; that if you navigate over the candidate at hit RET, it will do what
;; the minibuffer would have done.  In contrast, the `embark-export'
;; command reads the metadata to figure out what category this is and
;; places them in a buffer whose major mode is specialised for that
;; type of content.  For example, when we are completing against
;; files, the export will take us to a `dired-mode' buffer; when we
;; preview the results of a grep, the export will put us in a
;; `grep-mode' buffer.
;;
(use-package embark
  :ensure t
  :bind (("C-." . embark-act)
         :map minibuffer-local-map
         ("C-c C-c" . embark-collect)
         ("C-c C-e" . embark-export)))

(setopt tab-always-indent 'complete)

(use-package corfu
  :hook
  (after-init . global-corfu-mode)
  :custom
  (corfu-cycle t) ; cycle around to first entry after reaching the last
  (corfu-preview-current nil) ; don't expand text at point until I press return
  (corfu-min-width 20)
  (corfu-on-exact-match 'insert) ; complete if there is only a single candidate
  (corfu-quit-no-match t)
  (corfu-quit-at-boundary t)
  :config
  (setopt corfu-popupinfo-delay '(1.25 . 0.5))
  (corfu-popupinfo-mode 1) ; shows documentation next to completions

  ;; sort by input history
  (with-eval-after-load 'savehist
    (corfu-history-mode 1)
    (add-to-list 'savehist-additional-variables 'corfu-history))
  )

(use-package cape
  :defer t
  :config
  (add-hook 'completion-at-point-functions #'cape-dabbrev 20) ; words from buffer
  (add-hook 'completion-at-point-functions #'cape-file 20))

(use-package dired
  :ensure nil
  :commands (dired)
  :config
  (setq  dired-kill-when-opening-new-dired-buffer t
         dired-listing-switches "-AGFhlv --group-directories-first --time-style=long-iso"))

(use-package recentf
  :ensure nil
  :config
  (setopt recentf-auto-cleanup 'never
          recentf-max-menu-items 0
          recentf-max-saved-items 200
	      recentf-save-file (bc-emacs-cache-dir "recentf"))
  (recentf-mode t))

(setopt save-interprogram-paste-before-kill t ; save the existing clipboard into the kill ring before overwriting it
	    kill-do-not-save-duplicates t
	    )

(setopt vc-follow-symlinks t)
(use-package magit)

(use-package treemacs
  :bind
  (("<f11>" . treemacs)
   ("C-<f11>" . treemacs-select-window))
  :hook
  ((treemacs-mode . treemacs-project-follow-mode)
   (treemacs-mode . treemacs-follow-mode))
  :config
  (setopt treemacs-persist-file (bc-emacs-cache-dir "treemacs/persist")
          treemacs-is-never-other-window t))

(use-package project
  :init
  (setq project-vc-extra-root-markers '("Cargo.toml" "pyproject.toml" "requirements.txt" "go.mod" "main.tf" "Makefile"))
  :config
  (setopt project-list-file (bc-emacs-cache-dir "projects.el")))

(repeat-mode 1)

;; prevent C-z from sending emacs to background
(global-unset-key (kbd "C-z"))

;; ace-window (switch between windows and frames)
(global-set-key (kbd "M-o") 'ace-window)

(use-package org
  :ensure nil
  :config
  (setopt
   org-adapt-indentation t
   org-confirm-babel-evaluate nil
   org-hide-block-startup t
   org-startup-folded 'fold
   org-ellipsis "  ⤶"
   )
  )

(org-babel-do-load-languages 'org-babel-load-languages '(
                                                         (emacs-lisp . t)
                                                         (python . t))
                             )

;; add the option #+auto_tangle: t in org files to auto tangle
(use-package org-auto-tangle
  :defer t
  :hook
  (org-mode . org-auto-tangle-mode))

(use-package prog-mode
  :ensure nil
  :hook
  ((prog-mode . subword-mode) ; useful to move through camel case words
   (prog-mode . which-function-mode) ; show the function name in the modeline
   ))

(use-package eglot
  :ensure nil
  :functions (eglot-ensure)
  :commands (eglot)
  :hook
  (prog-mode . eglot-ensure)
  :config
  (set-face-attribute 'eglot-highlight-symbol-face nil
                      :foreground "#ffd700"
                      :underline t)
  )

(defun ansible-vault-mode-maybe ()
  (when (ansible-vault--is-encrypted-vault-file)
    (ansible-vault-mode 1)))

(use-package poly-ansible)

(use-package ansible-vault
  :init
  (add-hook 'yaml-mode-hook 'ansible-vault-mode-maybe)
  :config
  (setq ansible-vault-password-file "~/.ansible/vault-password"))

(use-package dockerfile-mode)

(use-package go-ts-mode
  :init
  (add-to-list 'treesit-language-source-alist '(go "https://github.com/tree-sitter/tree-sitter-go"))
  (add-to-list 'treesit-language-source-alist '(gomod "https://github.com/camdencheek/tree-sitter-go-mod"))
  (add-to-list 'auto-mode-alist '("\\.go\\'" . go-ts-mode))
  (add-to-list 'auto-mode-alist '("/go\\.mod\\'" . go-mod-ts-mode))
  :hook
  ((go-ts-mode . eglot-ensure)
   (go-ts-mode . go-format-on-save-mode))
  :config
  (reformatter-define go-format
                      :program "goimports"
                      :args '("/dev/stdin"))
  )

(use-package sops
  :ensure t
  :bind (("C-c C-c" . sops-save-file)
         ("C-c C-k" . sops-cancel)
         ("C-c C-d" . sops-edit-file))
  :init
  (global-sops-mode 1))

(use-package terraform-mode
  :config
  (setopt terraform-indent-level 2)
  :hook
  (terraform-mode . terraform-format-on-save))

(use-package yaml-mode
  :hook
  (yaml-mode . (lambda ()
                 (electric-indent-local-mode -1))))

(setopt eshell-directory-name (bc-emacs-cache-dir "eshell"))

(use-package vterm
  :ensure t
  :custom
  (vterm-max-scrollback 100000)
  )
