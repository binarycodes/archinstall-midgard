#!/usr/bin/env bash

# Pick the default PipeWire audio output.

mapfile -t sinks < <(pw-dump | jq -r '
  .[]
  | select(.type == "PipeWire:Interface:Node")
  | select(.info.props["media.class"] == "Audio/Sink")
  | "\(.id)\t\(.info.props["node.description"] // .info.props["node.name"])"
')

if [ "${#sinks[@]}" -eq 0 ]; then
    notify-send "Audio" "No output devices"
    exit 0
fi

current=$(wpctl inspect @DEFAULT_AUDIO_SINK@ | awk 'NR==1 { gsub(",", "", $2); print $2 }')

ids=()
names=()
labels=()

for sink in "${sinks[@]}"; do
    id=${sink%%$'\t'*}
    name=${sink#*$'\t'}

    if [ "$id" = "$current" ]; then
        label="󰄬 $name"
    else
        label="  $name"
    fi

    ids+=("$id")
    names+=("$name")
    labels+=("$label")
done

chosen=$(printf '%s\n' "${labels[@]}" | wofi --dmenu --prompt "Audio output")

if [ -z "$chosen" ]; then
    exit 0
fi

for i in "${!labels[@]}"; do
    if [ "${labels[$i]}" = "$chosen" ]; then
        wpctl set-default "${ids[$i]}"
        notify-send "Audio" "Output: ${names[$i]}"
        exit 0
    fi
done
