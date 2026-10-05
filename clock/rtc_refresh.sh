#!/bin/sh

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8
export KC_OUT=/mnt/us/linkss/screensavers/bg_ss00.png
export KC_EIPS=0
export KC_FONT_SANS=/mnt/us/clock/fonts/NotoSansCJK-RegularSC-sans-sub.otf
export KC_FONT_SERIF=/mnt/us/clock/fonts/NotoSerifCJK-RegularSC-serif-sub.otf

FLAG=/tmp/clock_ss_on
LOG=/tmp/clock_rtc.log
WAKE1=${KC_RTC_DEV:-/sys/class/rtc/rtc1/wakealarm}
WAKE2=${KC_RTC_DEV2:-/sys/class/rtc/rtc2/wakealarm}
LAST_FILE=/tmp/clock_last_loop
ENABLE=${KC_RTC:-1}
PERIOD=${KC_RTC_PERIOD:-300}
NIGHT_H=${KC_NIGHT_FETCH_H:-04}
NIGHT_WAIT=${KC_NIGHT_FETCH_WAIT:-60}

Note() { echo ">> $(date '+%H:%M:%S') $*" >>"$LOG"; }

sync_snvs() {
    _now=$(date +%s)
    _r=$(cat /sys/class/rtc/rtc2/since_epoch 2>/dev/null)
    case "$_r" in ''|*[!0-9]*) return 1;; esac
    _d=$(( _now - _r ))
    [ "$_d" -lt 0 ] && _d=$(( -_d ))
    [ "$_d" -gt 30 ] || return 0

    _last=$(cat /tmp/clock_snvs_sync 2>/dev/null)
    case "$_last" in ''|*[!0-9]*) _last=0;; esac
    [ $(( _now - _last )) -lt 60 ] && return 1
    date +%s > /tmp/clock_snvs_sync
    /sbin/hwclock -w -f /dev/rtc2 --utc 2>/dev/null
    Note "SNVS-SYNC drift=${_d}s -> hwclock -w (rtc2 was $_r, now $(cat /sys/class/rtc/rtc2/since_epoch 2>/dev/null))"
    return 1
}

arm_alarm() {
    _next=$1
    _ok=""
    sync_snvs
    for _w in "$WAKE1" "$WAKE2"; do
        [ -w "$_w" ] || continue

        _t=$_next
        [ "$_w" = "$WAKE2" ] && _t=$(( _next + 30 ))
        _n=0
        while [ "$_n" -lt 3 ]; do
            echo 0 > "$_w" 2>/dev/null
            echo "$_t" > "$_w" 2>/dev/null
            _got=$(cat "$_w" 2>/dev/null)
            if [ -n "$_got" ] && [ "$_got" -gt 0 ] 2>/dev/null && \
               [ $(( _t - _got )) -le 3 ] && [ $(( _got - _t )) -le 3 ]; then
                _tag=${_w#/sys/class/rtc/}
                _ok="$_ok ${_tag%/wakealarm}"
                break
            fi
            _n=$(( _n + 1 ))
            sleep 1
        done
    done
    if [ -n "$_ok" ]; then
        echo "OK $_next$_ok"
        return 0
    fi
    echo "FAIL want=$_next got1=$(cat "$WAKE1" 2>/dev/null) got2=$(cat "$WAKE2" 2>/dev/null)"
    return 1
}

wifi_state() { lipc-get-prop com.lab126.wifid cmState 2>/dev/null | tr -d '\r\n'; }

wifi_set() {
    _v=$1
    lipc-set-prop -i com.lab126.cmd wirelessEnable "$_v" >/dev/null 2>&1
    lipc-set-prop -i com.lab126.wifid enable       "$_v" >/dev/null 2>&1
    lipc-set-prop    com.lab126.wifid enable       "$_v" >/dev/null 2>&1
}

night_fetch() {
    [ -f "$FLAG" ] || return 0
    [ "$(date +%H)" = "$NIGHT_H" ] || return 0
    _mark=/tmp/clock_nightfetch_$(date +%F)
    [ -f "$_mark" ] && return 0
    date +%s > "$_mark"

    _was=$(wifi_state)
    Note "NIGHT-FETCH begin wifi_before=$_was"

    ka() { arm_alarm $(( $(date +%s) + 25 )) >/dev/null 2>&1; }

    ka
    wifi_set 1

    _i=0
    while [ "$_i" -lt "$NIGHT_WAIT" ]; do
        _s=$(wifi_state)
        case "$_s" in *CONNECTED*) break;; esac
        ka
        sleep 3
        _i=$(( _i + 3 ))
    done

    if [ "$_i" -lt "$NIGHT_WAIT" ]; then
        python3 /mnt/us/clock/fetch_daily.py >>"$LOG" 2>&1 &
        _pid=$!
        while [ -d "/proc/$_pid" ]; do ka; sleep 5; done
        wait "$_pid"
        _rc=$?
        Note "NIGHT-FETCH fetch rc=$_rc (wifi 等待 ${_i}s, wifi=$_s)"
    else
        Note "NIGHT-FETCH no-net after ${NIGHT_WAIT}s (wifi=$_s) —— 白天解锁时兜底"
    fi

    case "$_was" in
        *CONNECTED*) Note "NIGHT-FETCH end wifi_left=on (进来时就是开的，不动它)" ;;
        *)           wifi_set 0; Note "NIGHT-FETCH end wifi_restored=off" ;;
    esac
}

Note "loop start period=${PERIOD}s enable=${ENABLE} dev1=$WAKE1 dev2=$WAKE2"
sync_snvs

while true; do
    now=$(date +%s)
    next=$(( (now / PERIOD + 1) * PERIOD ))
    [ $(( next - now )) -lt 20 ] && next=$(( next + PERIOD ))

    arm=$(arm_alarm "$next")
    case "$arm" in
        OK*) Note "arm target=$(date -d @${next} '+%H:%M:%S') ${arm}" ;;
        *)   Note "ARM-FAIL ${arm} target=$(date -d @${next} '+%H:%M:%S')" ;;
    esac

    while [ "$(date +%s)" -lt "$next" ]; do
        sleep 5
        arm2=$(arm_alarm "$next")
        case "$arm2" in
            OK*) ;;
            *)   Note "ARM-FAIL(keepalive) ${arm2}" ;;
        esac
    done

    if [ -f "$LAST_FILE" ]; then
        last=$(cat "$LAST_FILE" 2>/dev/null)
        if [ -n "$last" ] && [ "$last" -gt 0 ] 2>/dev/null; then
            gap=$(( $(date +%s) - last ))
            if [ "$gap" -gt $(( PERIOD * 2 + 120 )) ]; then
                Note "WAKE-GAP ${gap}s (~$(( gap / 60 ))min) —— 闹钟疑似失效过"
            fi
        fi
    fi
    date +%s > "$LAST_FILE"

    python3 /mnt/us/clock/fetch_daily.py >>"$LOG" 2>&1

    night_fetch

    if [ -f "$FLAG" ]; then
        if [ "$ENABLE" = "1" ]; then
            env KC_EIPS=1 \
                python3 /mnt/us/clock/kindle_clock.py >>"$LOG" 2>&1
            Note "rtc-refresh eips"
        else
            python3 /mnt/us/clock/kindle_clock.py >>"$LOG" 2>&1
            Note "rtc-refresh no-eips(disabled)"
        fi
    else
        Note "skip (not in screensaver)"
    fi

    sleep 5
done
