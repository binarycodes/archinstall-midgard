#!/bin/bash

weather=$(curl -s "wttr.in/?format=%c%t" 2>/dev/null)

if [ -z "$weather" ] || echo "$weather" | grep -q "Unknown"; then
    echo '{"text": "N/A", "tooltip": "Weather unavailable"}'
    exit 0
fi

tooltip=$(curl -s "wttr.in/?format=%l:+%C+%t+%h+%w" 2>/dev/null)

printf '{"text": "%s", "tooltip": "%s"}\n' "$weather" "$tooltip"
