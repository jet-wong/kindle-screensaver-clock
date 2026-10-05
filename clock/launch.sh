#!/bin/sh

mkdir -p /mnt/us/linkss/screensavers

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8
export KC_OUT=/mnt/us/linkss/screensavers/bg_ss00.png
export KC_EIPS=0

export KC_FONT_SANS=/mnt/us/clock/fonts/NotoSansCJK-RegularSC-sans-sub.otf
export KC_FONT_SERIF=/mnt/us/clock/fonts/NotoSerifCJK-RegularSC-serif-sub.otf

LOOP_SEC=${KC_LOOP_SEC:-60}

while true; do
  python3 /mnt/us/clock/fetch_daily.py
  python3 /mnt/us/clock/kindle_clock.py
  sleep "$LOOP_SEC"
done
