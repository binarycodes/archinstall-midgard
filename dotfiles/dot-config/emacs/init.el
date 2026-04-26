;;; init.el -*- lexical-binding: t; -*-

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

(setopt tramp-persistency-file-name (bc-emacs-cache-dir "tramp/persist")
        tramp-histfile-override (bc-emacs-cache-dir "tramp/history"))

(setopt svg-lib-icons-dir (bc-emacs-cache-dir "svg-lib"))

;; disable fancy gui stuffs, menu et. all and other ui configs
(menu-bar-mode -1)   ; disable the menu bar
(mouse-avoidance-mode 'banish) ; banish the cursor as soon as i am typing
(scroll-bar-mode -1) ; disable visible scrollbar
(tool-bar-mode -1)   ; disable the toolbar
(tooltip-mode -1)    ; disable tooltips

;; theme
(use-package ef-themes
  :ensure t
  :demand t
  :init
  (ef-themes-take-over-modus-themes-mode 1)
  :bind
  (("<f5>" . modus-themes-rotate)
   ("C-<f5>" . modus-themes-select)
   ("M-<f5>" . modus-themes-load-random))
  :config
  ;; All customisations here.
  (setq modus-themes-mixed-fonts t)
  (setq modus-themes-italic-constructs t))

(defun bc-load-theme ()
  (if (display-graphic-p)
      (modus-themes-load-theme 'ef-owl)
    (modus-themes-load-theme 'ef-owl)))

;; if emacs is running as daemon, then setting font dont work till frame is created
(if (daemonp)
    (add-hook 'server-after-make-frame-hook #'bc-load-theme)
  (bc-load-theme))

;; fonts/faces
(defun bc-set-font-faces ()
  (cond
   ((eq system-type 'darwin)
    (set-face-attribute 'default nil :font "JetBrainsMono Nerd Font" :height 120)
    (set-face-attribute 'fixed-pitch nil :font "JetBrainsMono Nerd Font" :height 120)
    (set-face-attribute 'variable-pitch nil :font "Roboto" :height 120 :weight 'regular))
   (t
    (set-face-attribute 'default nil :font "JetBrainsMono Nerd Font" :height 120)
    (set-face-attribute 'fixed-pitch nil :font "JetBrainsMono Nerd Font" :height 120)
    (set-face-attribute 'variable-pitch nil :font "Roboto" :height 120 :weight 'regular))))

;; if emacs is running as daemon, then setting font dont work till frame is created
(if (daemonp)
    (add-hook 'server-after-make-frame-hook #'bc-set-font-faces)
  (bc-set-font-faces))

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

(use-package doom-modeline
  :ensure t
  :config
  (doom-modeline-mode 1)
  :custom
  ((doom-modeline-height 15)
   (doom-modeline-icon t)))

(use-package spacious-padding
  :ensure t
  :custom
  (spacious-padding-subtle-mode-line t)
  (spacious-padding-widths '(
                             :internal-border-width 5
                             :header-line-width 4
                             :mode-line-width 6
                             :custom-button-width 3
                             :tab-width 4
                             :right-divider-width 1
                             :scroll-bar-width 8
                             :fringe-width 8))
  :config
  (spacious-padding-mode 1))

(use-package server
  :ensure nil
  :defer 1
  :config
  (setopt server-client-instructions nil)
  (unless (server-running-p)
    (server-start))
  )

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

;; more marks are always better
(setopt mark-ring-max 1000
        global-mark-ring-max 2000)

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

(use-package markdown-mode
  :ensure t
  :defer t
  :config
  (setq markdown-fontify-code-blocks-natively t)
  )

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
  :bind (("M-s M-g" . consult-ripgrep) ; a recursive grep
         ("M-s M-f" . consult-fd) ; search for files names recursively
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
  (corfu-on-exact-match 'show) ; complete if there is only a single candidate
  (corfu-quit-no-match t)
  (corfu-quit-at-boundary t)
  :config
  (setopt corfu-auto t
          corfu-auto-delay 0.2
          corfu-auto-prefix 1
          corfu-preselect 'prompt
          )
  (corfu-popupinfo-mode 1) ; shows documentation next to completions

  ;; sort by input history
  (with-eval-after-load 'savehist
    (corfu-history-mode 1)
    (add-to-list 'savehist-additional-variables 'corfu-history))
  )

(use-package kind-icon
  :after corfu
  :config
  (add-to-list 'corfu-margin-formatters #'kind-icon-margin-formatter))

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
  (dolist (pattern `(,(bc-emacs-cache-dir "*") "/tmp/zsh.*\\.zsh"))
    (add-to-list 'recentf-exclude pattern))
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
  (setq project-vc-extra-root-markers '("Cargo.toml" "pyproject.toml" "requirements.txt" "go.mod"))
  :config
  (setopt project-list-file (bc-emacs-cache-dir "projects.el")))

(repeat-mode 1)

;; prevent C-z from sending emacs to background
(global-unset-key (kbd "C-z"))

;; ace-window (switch between windows and frames)
(global-set-key (kbd "M-o") 'ace-window)

(use-package which-key
  :ensure t
  :init
  (which-key-mode)
  :config
  (setq which-key-idle-delay 0.1
        which-key-idle-secondary-delay 0.05
        which-key-sort-order 'which-key-key-order-alpha
        which-key-max-description-length 40))

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
   (prog-mode . completion-preview-mode) ; show inline completion preview
   ))

(use-package reformatter
  :ensure t)

(use-package treesit
  :ensure nil
  :config
  (setopt treesit-font-lock-level 3)
  ;; Define grammar sources
  (setq treesit-language-source-alist
        '((css . ("https://github.com/tree-sitter/tree-sitter-css" "v0.20.0"))
          (html . ("https://github.com/tree-sitter/tree-sitter-html" "v0.20.1"))
          (javascript . ("https://github.com/tree-sitter/tree-sitter-javascript" "v0.20.1" "src"))
          (json . ("https://github.com/tree-sitter/tree-sitter-json" "v0.20.2"))
          (python . ("https://github.com/tree-sitter/tree-sitter-python" "v0.20.4"))
          (toml . ("https://github.com/tree-sitter/tree-sitter-toml" "v0.5.1"))
          (tsx . ("https://github.com/tree-sitter/tree-sitter-typescript" "v0.20.3" "tsx/src"))
          (typescript . ("https://github.com/tree-sitter/tree-sitter-typescript" "v0.20.3" "typescript/src"))
          (yaml . ("https://github.com/ikatyang/tree-sitter-yaml" "v0.5.0"))
          (go . ("https://github.com/tree-sitter/tree-sitter-go"))
          (gomod . ("https://github.com/camdencheek/tree-sitter-go-mod"))

          (elisp "https://github.com/Wilfred/tree-sitter-elisp")
          (bash "https://github.com/tree-sitter/tree-sitter-bash")
          (cmake "https://github.com/uyha/tree-sitter-cmake")
          (rust "https://github.com/tree-sitter/tree-sitter-rust")
          (make "https://github.com/alemuller/tree-sitter-make")
          (markdown "https://github.com/ikatyang/tree-sitter-markdown")

          (heex "https://github.com/phoenixframework/tree-sitter-heex")
          (elixir "https://github.com/elixir-lang/tree-sitter-elixir")))
  ;; Remap major modes to their tree-sitter counterparts
  (dolist (mapping
           '((python-mode . python-ts-mode)
             (css-mode . css-ts-mode)
             (typescript-mode . typescript-ts-mode)
             (js2-mode . js-ts-mode)
             (bash-mode . bash-ts-mode)
             (conf-toml-mode . toml-ts-mode)
             (go-mode . go-ts-mode)
             (json-mode . json-ts-mode)
             (js-json-mode . json-ts-mode)
             (elixir-mode . elixir-ts-mode)))
    (add-to-list 'major-mode-remap-alist mapping))
  )

(setq treesit--install-grammar-directory
      (bc-emacs-cache-dir "treesitter"))

(defun bc-treesitter-config-reinstall-grammars ()
  "Force reinstallation of all grammars in `treesit-language-source-alist'.
  Use this to update grammars to their latest versions."
  (interactive)
  (dolist (lang-source treesit-language-source-alist)
    (let ((lang (car lang-source)))
      (message "Treesitter: Reinstalling grammar for %s..." lang)
      (cl-letf (((symbol-function 'y-or-n-p) (lambda (&rest _) t)))
        (treesit-install-language-grammar lang)))))

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
  (setq eglot-workspace-configuration
        '(:java (:completion (:guessMethodArguments :json-false))))
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

(use-package eat
  :ensure t
  :bind (("C-c t" . eat))
  :config
  (setq eat-kill-buffer-on-exit t))

(use-package elfeed
  :ensure t
  :bind
  (("C-c r e" . elfeed))
  :config
  (setq elfeed-db-directory (bc-emacs-cache-dir "elfeed-db")
        elfeed-feeds
        '(("https://karthinks.com/index.xml" dev emacs)
          ("https://feeds.feedburner.com/TheHackersNews" security cyber tech news)
          ("https://feed.itsfoss.com/" linux tech news)
          ("https://www.apalrd.net/index.xml" tech blog))))

(use-package eww
  :ensure nil
  :init
  (setopt browse-url-browser-function 'browse-url-default-browser
          url-configuration-directory (bc-emacs-cache-dir "url")
          url-cookie-file (bc-emacs-cache-dir "url/cookies"))
  :config
  (setopt eww-auto-rename-buffer 'title
          browse-url-browser-function 'eww-browse-url))

(use-package olivetti)
