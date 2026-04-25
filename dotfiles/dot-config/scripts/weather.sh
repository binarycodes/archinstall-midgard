#!/usr/bin/env bash

# Thanks to
# https://gist.github.com/marcos-inja/2b07767ff079d4f39fc71be4b0c92903

declare -A WEATHER_CODES=(
  [113]=""
  [116]=""
  [119]=""
  [122]=""
  [143]=""
  [176]=""
  [179]=""
  [182]=""
  [185]=""
  [200]=""
  [227]=""
  [230]=""
  [248]=""
  [260]=""
  [263]=""
  [266]=""
  [281]=""
  [284]=""
  [293]=""
  [296]=""
  [299]=""
  [302]=""
  [305]=""
  [308]=""
  [311]=""
  [314]=""
  [317]=""
  [320]=""
  [323]=""
  [326]=""
  [329]=""
  [332]=""
  [335]=""
  [338]=""
  [350]=""
  [353]=""
  [356]=""
  [359]=""
  [362]=""
  [365]=""
  [368]=""
  [371]=""
  [374]=""
  [377]=""
  [386]=""
  [389]=""
  [392]=""
  [395]=""
)

weather_json=$(curl -s "https://wttr.in/$LOCATION?format=j1")

code=$(echo "$weather_json" | jq -r '.current_condition[0].weatherCode')
desc=$(echo "$weather_json" | jq -r '.current_condition[0].weatherDesc[0].value')
temp=$(echo "$weather_json" | jq -r '.current_condition[0].temp_C')
feels=$(echo "$weather_json" | jq -r '.current_condition[0].FeelsLikeC')
hum=$(echo "$weather_json" | jq -r '.current_condition[0].humidity')
wind=$(echo "$weather_json" | jq -r '.current_condition[0].windspeedKmph')
winddir=$(echo "$weather_json" | jq -r '.current_condition[0].winddir16Point')
area=$(echo "$weather_json" | jq -r '.nearest_area[0].areaName[0].value')
country=$(echo "$weather_json" | jq -r '.nearest_area[0].country[0].value')

icon="${WEATHER_CODES[$code]:-}"

tooltip="$desc\rFeels like: ${feels}°C\rHumidity: ${hum}%\rWind: ${wind}km/h ${winddir}\r${area}, ${country}"

echo "{\"text\": \"$icon ${temp}°C\", \"tooltip\": \"$tooltip\"}"
