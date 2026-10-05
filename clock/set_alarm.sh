#!/bin/sh

WAKE1=${KC_RTC_DEV:-/sys/class/rtc/rtc1/wakealarm}
WAKE2=${KC_RTC_DEV2:-/sys/class/rtc/rtc2/wakealarm}
PERIOD=${KC_RTC_PERIOD:-300}

now=$(date +%s)
next=$(( (now / PERIOD + 1) * PERIOD ))

[ $(( next - now )) -lt 20 ] && next=$(( next + PERIOD ))

set_one() {
    _w=$1
    _t=$2
    _left=3
    while [ "$_left" -gt 0 ]; do
        echo 0 > "$_w" 2>/dev/null
        echo "$_t" > "$_w" 2>/dev/null
        _got=$(cat "$_w" 2>/dev/null)
        if [ -n "$_got" ] && [ "$_got" -gt 0 ] 2>/dev/null; then
            if [ $(( _t - _got )) -le 3 ] && [ $(( _got - _t )) -le 3 ]; then
                return 0
            fi
        fi
        _left=$(( _left - 1 ))
        sleep 1
    done
    return 1
}

_r=$(cat /sys/class/rtc/rtc2/since_epoch 2>/dev/null)
case "$_r" in
    ''|*[!0-9]*) ;;
    *)
        _d=$(( now - _r ))
        [ "$_d" -lt 0 ] && _d=$(( -_d ))
        [ "$_d" -gt 30 ] && /sbin/hwclock -w -f /dev/rtc2 --utc 2>/dev/null
        ;;
esac

ok=""
[ -w "$WAKE1" ] && set_one "$WAKE1" "$next" && ok="$ok rtc1"

[ -w "$WAKE2" ] && set_one "$WAKE2" $(( next + 30 )) && ok="$ok snvs"

if [ -n "$ok" ]; then
    echo "OK $next$ok"
    exit 0
fi

echo "FAIL want=$next got1=$(cat "$WAKE1" 2>/dev/null) got2=$(cat "$WAKE2" 2>/dev/null)"
exit 1
