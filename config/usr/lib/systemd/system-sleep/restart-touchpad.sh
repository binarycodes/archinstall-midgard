#!/usr/bin/env bash

has_touchpad() {
  grep -qi touchpad /proc/bus/input/devices
}

if [[ "${1:-}" == post ]] && has_touchpad; then
    rmmod psmouse
    modprobe psmouse
fi
