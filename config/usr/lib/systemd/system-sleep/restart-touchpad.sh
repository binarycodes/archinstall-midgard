#!/usr/bin/env bash

if [[ $1 == post ]]; then
    sudo rmmod psmouse
    sudo modprobe psmouse
fi
