# Kindle PW2 Screensaver Clock (kindle-clock)

[中文](README.md) | English

Renders **time / Gregorian date / Chinese lunar calendar + sexagenary cycle / solar terms / poetry / English quote** into a screensaver image on a jailbroken Kindle Paperwhite 2 (758×1024 e-ink), displayed by the linkss screensaver hack.

**Lock the screen and you get a clock — and the time keeps ticking while the device sleeps.**

![preview](preview.png)

## Features

- **A frozen clock is the default behavior**: when a Kindle suspends, every userspace process is frozen, so ordinary solutions leave the screensaver stuck at the moment you locked it. This project uses hardware RTC alarms to wake the device on a schedule, re-render, and repaint, advancing the screensaver clock every 5 minutes.
- **Paints only while the screensaver is up**: rendering writes the PNG only. The framebuffer is repainted via `eips` **only** when the device is confirmed to be sitting in the screensaver (a `goingToScreenSaver` event was received and `outOfScreenSaver` was not). It will never cover the page you are reading.
- **Content refreshes daily**: poetry (jinrishici) plus an English quote (adviceslip / zenquotes); if the network is unreachable it falls back to a rotating local set, so the screen is never blank. At 4 AM it briefly turns WiFi on, fetches the day's content, then puts WiFi back the way it found it.
- **Fixed to Beijing time**: does not depend on the device timezone. Lunar calendar, sexagenary cycle, and solar terms are all computed offline (Meeus algorithms), with no external dependency.
- **Dual-channel RTC alarm + watchdog**: rtc1 (PMIC alarm1) is primary, rtc2 (SNVS, independent interrupt) is a backup offset by 30 seconds. The alarm is rewritten every 5 seconds while waiting, and a wake-gap self-check (`WAKE-GAP`) tells you at a glance whether the alarm failed or the device simply was not locked.

## Repository layout

```
kindle-clock/
├── README.md
├── README.en.md
├── preview.png                  preview image
└── clock/                       ← copy this whole directory to /mnt/us/clock/ on the device
    ├── kindle_clock.py          main renderer (758×1024 PNG; lunar/sexagenary/solar-term/poetry layout)
    ├── fetch_daily.py           daily content fetch (poetry + English quote → daily.json)
    ├── launch.sh                awake loop: render + fetch content (no repaint)
    ├── watch_ss.sh              listens for screensaver enter/exit events, renders on lock, maintains /tmp/clock_ss_on
    ├── rtc_refresh.sh           sleep loop: RTC alarm wake + eips repaint (the only place that repaints)
    ├── set_alarm.sh             manually set an alarm (for debugging; rtc_refresh.sh has the same logic inlined)
    ├── install.sh               one-shot on-device installer (installs upstart configs and starts the three jobs)
    ├── cacert.pem               CA bundle (jailbroken devices ship no system certificates)
    ├── fonts/
    │   ├── NotoSansCJK-RegularSC-sans-sub.otf
    │   └── NotoSerifCJK-RegularSC-serif-sub.otf
    └── init/                    ← copied to /etc/init/ during install
        ├── clock_loop.conf      job: clock_loop   → launch.sh
        ├── clock_watch.conf     job: clock_watch  → watch_ss.sh
        └── clock_rtc.conf       job: clock_rtc    → rtc_refresh.sh
```

All three upstart jobs use `start on started framework` + `respawn` (5 times / 300 seconds): they start at boot and are restarted automatically if they crash.

## How it works

```
┌─ clock_watch (watch_ss.sh) ── watches powerd events ─────────┐
│   goingToScreenSaver → create /tmp/clock_ss_on → render → eips repaint
│   outOfScreenSaver   → delete the flag (nobody may repaint after this) │
└──────────────────────────────────────────────────────────────┘
┌─ clock_loop (launch.sh) ── every 60s while awake ────────────┐
│   fetch_daily.py (actually fetches only when online) → kindle_clock.py (PNG only) │
└──────────────────────────────────────────────────────────────┘
┌─ clock_rtc (rtc_refresh.sh) ── every 300s while asleep ──────┐
│   write rtc1/rtc2 hardware alarms → device suspends → woken at the alarm
│   → confirm still in screensaver → render + eips repaint → next round │
└──────────────────────────────────────────────────────────────┘
```

Key points:

- **Screensaver flag `/tmp/clock_ss_on`**: only `watch_ss.sh` sets and clears it, and only on a real event. `rtc_refresh.sh` checks this flag before every repaint, so the screen is never repainted while you are reading.
- **Dual-channel alarm**: rtc1 (`/sys/class/rtc/rtc1/wakealarm`) is written with an absolute epoch, but it shares an interrupt mask bit with alarm0, which powerd owns exclusively, so it is occasionally masked out. rtc2 (`/sys/class/rtc/rtc2/wakealarm`, SNVS, independent power domain and interrupt) fires 30 seconds later as a fallback. rtc2's hardware time base ships as 1970, so **its base is validated before every alarm write, and if the drift exceeds 30s it is resynced with `hwclock -w --utc`**.
- **The alarm is rewritten every 5 seconds while waiting**: whoever writes the alarm last decides whether it fires during suspend, so writing frequently shrinks the window in which powerd can mask it to a minimum.
- **4 AM fetch**: that round briefly enables WiFi, fetches the day's content, then restores WiFi to the state it was found in. It tries only once per day, and during the fetch it pushes the alarm to now+25s every 5 seconds so a mid-fetch suspend cannot leave the device asleep.

## Requirements

| Requirement | Notes |
|---|---|
| Jailbreak + root | needed for `mntroot rw` to modify `/etc/init/` |
| Python 3 + Pillow | `python3 -c "import PIL"` must succeed on the device |
| linkss screensaver hack | provides the screensaver image mechanism (only reads `/mnt/us/linkss/screensavers/bg_ssNN.png`) |
| Free rtc1 / rtc2 | rtc0 is owned exclusively by powerd and must not be touched |
| A saved WiFi network | the 4 AM fetch needs the device to reconnect automatically |

## Installation

### 1. Copy the files

Connect the Kindle over USB and copy the entire `clock/` directory to the user partition:

```
kindle → /mnt/us/clock/
```

After copying, the device should contain:

```
/mnt/us/clock/kindle_clock.py
/mnt/us/clock/fetch_daily.py
/mnt/us/clock/launch.sh
/mnt/us/clock/watch_ss.sh
/mnt/us/clock/rtc_refresh.sh
/mnt/us/clock/set_alarm.sh
/mnt/us/clock/install.sh
/mnt/us/clock/cacert.pem
/mnt/us/clock/fonts/*.otf
/mnt/us/clock/init/*.conf
```

Or push over SSH:

```sh
ssh root@192.168.x.x "mkdir -p /mnt/us/clock"
scp -r clock/* root@192.168.x.x:/mnt/us/clock/
```

### 2. Install on the device

SSH into the device (or open a shell from KUAL) and run:

```sh
sh /mnt/us/clock/install.sh
```

The script will: verify file integrity → check Pillow → `mntroot rw` → copy the three `.conf` files to `/etc/init/` → start the three jobs → print status → run a render self-test.

### 3. Verify

Lock the screen once; the screensaver should turn into the clock image. Then unlock and lock again — the time shown should be the exact moment you locked it.

Refreshing every 5 minutes during sleep takes a while to observe: lock the screen, leave it alone, and check again after about 10 minutes.

## Configuration (environment variables)

All of these are set in `clock/init/*.conf` (after editing, run `initctl reload-configuration` and restart the job), or exported at runtime.

### kindle_clock.py

| Variable | Default | Description |
|---|---|---|
| `KC_OUT` | `/mnt/us/linkss/screensavers/bg_ss00.png` | output PNG path (also accepts argv[1]) |
| `KC_EIPS` | `0` | `1` = repaint via eips right after rendering |
| `KC_SLOGAN` | `Take it easy.` | fallback English line at the bottom (overridden when remote content was fetched) |
| `KC_DAILY` | `/mnt/us/clock/daily.json` | path to the daily content cache |
| `KC_ROUND5` | `0` | `1` = round the time to 5 minutes |
| `KC_FONT_SANS` / `KC_FONT_SERIF` | `fonts/*.otf` | sans-serif / serif font paths |
| `KC_PNG_LEVEL` | `1` | PNG compression level (higher is slower and smaller) |

### rtc_refresh.sh

| Variable | Default | Description |
|---|---|---|
| `KC_RTC` | `1` | master switch; `0` = update the PNG only, never repaint (power-saving mode) |
| `KC_RTC_PERIOD` | `300` | sleep-time refresh period in seconds; 300 = aligned to 5-minute marks |
| `KC_RTC_DEV` | `/sys/class/rtc/rtc1/wakealarm` | primary alarm channel |
| `KC_RTC_DEV2` | `/sys/class/rtc/rtc2/wakealarm` | backup alarm channel |
| `KC_NIGHT_FETCH_H` | `04` | hour of the nightly online fetch (Beijing time) |
| `KC_NIGHT_FETCH_WAIT` | `60` | maximum seconds to wait for WiFi to come up |

### launch.sh / fetch_daily.py

| Variable | Default | Description |
|---|---|---|
| `KC_LOOP_SEC` | `60` | awake-time render period in seconds |
| `KC_FETCH_FORCE` | `0` | `1` = force a fresh fetch (for debugging) |
| `KC_FETCH_TIMEOUT` | `12` | HTTP timeout in seconds |
| `KC_FETCH_RETRY_MIN` | `30` | retry interval after a failed fetch, in minutes |

## Logs and troubleshooting

| File | Contents |
|---|---|
| `/tmp/clock_rtc.log` | RTC loop: `arm target=HH:MM:SS OK <epoch> rtc1 snvs`, `rtc-refresh eips`, `WAKE-GAP`, `NIGHT-FETCH` |
| `/tmp/clock_ss.log` | screensaver events: `goingToScreenSaver` / `outOfScreenSaver` / `eips repaint` |
| `/tmp/clock_fetch.log` | content fetch: `fetch start ...` / `saved poem=...` |
| `/tmp/clock.log` | stdout of launch.sh |

Frequently used commands:

```sh
initctl status clock_loop clock_watch clock_rtc   # status of the three jobs
stop clock_rtc && start clock_rtc                 # restart the RTC refresh
python3 /mnt/us/clock/kindle_clock.py             # render once manually
KC_FETCH_FORCE=1 python3 /mnt/us/clock/fetch_daily.py   # force a content fetch
sh /mnt/us/clock/set_alarm.sh                     # set an alarm manually; "OK <epoch> rtc1 snvs" means it worked
grep WAKE-GAP /tmp/clock_rtc.log                  # a hit means the alarm failed at some point (normally only historical entries)
tail -f /tmp/clock_rtc.log                        # watch the sleep-time refresh cadence
```

`/tmp` is cleared on reboot; long-term logs live in `/var/log/upstart/clock_*.log`.

## Uninstall

```sh
mntroot rw
stop clock_loop; stop clock_watch; stop clock_rtc
rm -f /etc/init/clock_loop.conf /etc/init/clock_watch.conf /etc/init/clock_rtc.conf
initctl reload-configuration
mntroot ro
rm -rf /mnt/us/clock
```

## Known limitations

- **SSH is unreachable while the device is asleep, and that is normal**: WiFi is turned off by powerd during suspend, and the device is only woken briefly by the RTC alarm — too briefly for an SSH handshake to complete. Unlock the device before connecting to read logs.
- **If you never unlock all day**: normally the 4 AM fetch brings in the day's content automatically; if the fetch fails (no network at night, router off), the device fetches it before the first render after you unlock during the day.
- The screensaver filename must be `bg_ssNN.png` (a linkss convention); change `KC_OUT` if you want a different location.

## Font license

The two fonts under `fonts/` are derived from Noto Sans/Serif CJK SC, subsetted to roughly 240 glyphs, and are distributed under the [SIL Open Font License 1.1](https://scripts.sil.org/OFL). Original fonts © Google / Adobe.

## License

The code is released under the [MIT License](LICENSE).
