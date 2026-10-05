#!/bin/sh

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8
export KC_OUT=/mnt/us/linkss/screensavers/bg_ss00.png
export KC_EIPS=0
export KC_FONT_SANS=/mnt/us/clock/fonts/NotoSansCJK-RegularSC-sans-sub.otf
export KC_FONT_SERIF=/mnt/us/clock/fonts/NotoSerifCJK-RegularSC-serif-sub.otf

FLAG=/tmp/clock_ss_on

(
    while true; do
        if lipc-wait-event -s 86400 com.lab126.powerd outOfScreenSaver >/dev/null 2>&1; then
            rm -f "$FLAG"
            echo ">> $(date '+%H:%M:%S') outOfScreenSaver" >>/tmp/clock_ss.log
        fi
    done
) &

while true; do
    if lipc-wait-event -s 1800 com.lab126.powerd goingToScreenSaver >/dev/null 2>&1; then
        : > "$FLAG"
        echo ">> $(date '+%H:%M:%S') goingToScreenSaver" >>/tmp/clock_ss.log

        python3 /mnt/us/clock/kindle_clock.py >>/tmp/clock_ss.log 2>&1

        if [ -f "$FLAG" ]; then
            eips -f -g "$KC_OUT" >>/tmp/clock_ss.log 2>&1
            echo ">> $(date '+%H:%M:%S') eips repaint" >>/tmp/clock_ss.log
        else
            echo ">> $(date '+%H:%M:%S') skip repaint (already unlocked)" >>/tmp/clock_ss.log
        fi
    else
        echo ">> $(date '+%H:%M:%S') wait-timeout (no event; flag untouched)" >>/tmp/clock_ss.log
    fi

    sleep 1
done
