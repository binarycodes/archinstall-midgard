#!/bin/bash

# Toggles the wifi radio. Bound to right-click on the network module and to
# the custom/wifi module, which is the only one left on the bar once the
# radio is off and there is no ethernet.

if rfkill list wlan | grep -q "Hard blocked: yes"; then
    notify-send "Wi-Fi" "Blocked by the hardware switch"
    exit 0
fi

if rfkill list wlan | grep -q "Soft blocked: yes"; then
    sudo rfkill unblock wlan
    notify-send "Wi-Fi" "Enabled"
else
    sudo rfkill block wlan
    notify-send "Wi-Fi" "Disabled"
fi
