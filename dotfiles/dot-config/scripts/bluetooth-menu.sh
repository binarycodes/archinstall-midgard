#!/bin/bash

devices=$(bluetoothctl devices Paired | awk '{$1=""; $2=""; print substr($0,3)}')

if [ -z "$devices" ]; then
    notify-send "Bluetooth" "No paired devices"
    exit 0
fi

chosen=$(echo "$devices" | wofi --dmenu --prompt "Bluetooth")

if [ -z "$chosen" ]; then
    exit 0
fi

mac=$(bluetoothctl devices Paired | grep "$chosen" | awk '{print $2}')

if bluetoothctl info "$mac" | grep -q "Connected: yes"; then
    bluetoothctl disconnect "$mac"
    notify-send "Bluetooth" "Disconnected from $chosen"
else
    bluetoothctl connect "$mac"
    notify-send "Bluetooth" "Connected to $chosen"
fi
