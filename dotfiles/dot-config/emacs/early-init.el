;;; early-init.el -*- lexical-binding: t; -*-

(defun bc-ensure-env (vars)
  "Ensure environment variables are set, using fallback value if unset.
VARS is an alist of (VAR . FALLBACK) pairs."

  (dolist (pair vars)
    (let ((var (car pair))
          (fallback (cdr pair)))
      (unless (getenv var)
        (setenv var fallback)))))

(bc-ensure-env
 `(("XDG_CONFIG_HOME" . ,(expand-file-name "~/.config"))
   ("XDG_CACHE_HOME" . ,(expand-file-name "~/.cache"))))

(defun bc-emacs-cache-dir (subpath)
  "Return a full path to a subdirectory under XDG_CACHE_HOME."
  (file-name-concat (getenv "XDG_CACHE_HOME") "emacs" subpath))

(defun bc-emacs-config-dir (subpath)
  "Return a full path to a subdirectory under XDG_CONFIG_HOME."
  (file-name-concat (getenv "XDG_CONFIG_HOME") "emacs" subpath))

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
                           ("elpa" . "https://elpa.gnu.org/packages/")
                           ("nongnu" . "https://elpa.nongnu.org/nongnu/")))

(setopt gnutls-algorithm-priority "NORMAL:+VERS-TLS1.3")

;; Initialize the package system early
(package-initialize)

;; Set eln-cache dir
(when (boundp 'native-comp-eln-load-path)
  (startup-redirect-eln-cache (bc-emacs-cache-dir "eln-cache")))

(setopt use-package-always-ensure t)

(setopt custom-file (locate-user-emacs-file (bc-emacs-cache-dir "custom-vars.el")))
(load custom-file 'noerror 'nomessage)

(setopt
 blink-cursor-interval 0.7
 confirm-kill-emacs 'yes-or-no-p
 inhibit-startup-screen t
 inhibit-startup-message t
 initial-scratch-message ""
 inhibit-startup-echo-area-message (user-login-name)
 use-dialog-box nil
 use-short-answers t
 visible-bell nil ; do not flash the screen, when moving out of bounds, ex, pressing up when already at the first line.
 )

(defun display-startup-echo-area-message ()
  (message "Let the hacking begin!"))
