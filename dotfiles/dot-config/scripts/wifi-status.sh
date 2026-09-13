#!/usr/bin/env bash

# Waybar custom module for the wifi radio state.
#
# The built-in network module binds to an interface, so when the radio is
# rfkill'd and there is no ethernet it has nothing to bind to and hides
# itself completely - leaving nothing to click to switch wifi back on.
# This module reads rfkill instead, so it is there regardless.
#
# It stays empty (hidden) while the radio is on, so it never doubles up
# with the network module.
#
# Runs continuously: emits once, then again on every rfkill event. That
# covers the Fn-key hardware switch too, not just our own toggle script.

emit() {
    local state
    state=$(rfkill list wlan)

    if grep -q "Hard blocked: yes" <<< "$state"; then
        echo "{\"text\": \"󰖪 wifi off\", \"class\": \"hard-blocked\", \"tooltip\": \"wifi is blocked by the hardware switch\"}"
    elif grep -q "Soft blocked: yes" <<< "$state"; then
        echo "{\"text\": \"󰖪 wifi off\", \"class\": \"disabled\", \"tooltip\": \"wifi is off\rclick to turn it back on\"}"
    else
        echo "{\"text\": \"\"}"
    fi
}

emit

# stdbuf keeps rfkill line-buffered; into a pipe it would block-buffer and
# events would sit unflushed
stdbuf -oL rfkill event | while read -r _; do
    emit
done
