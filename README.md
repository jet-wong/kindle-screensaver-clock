# Kindle PW2 屏保时钟（kindle-clock）

中文 | [English](README.en.md)

在越狱 Kindle Paperwhite 2（758×1024 e-ink）上，把「时间 / 公历 / 农历+干支 / 节气 / 诗词 / 英文短句」渲染成屏保图，由 linkss 屏保 hack 显示。

**锁屏即见时钟，休眠期间时间照常走动。**

![preview](preview.png)

## 特性

- **休眠期间时间不走是常态**：Kindle 挂起时所有用户态进程被冻结，普通方案屏保只会停在锁屏那一刻。本项目用硬件 RTC 闹钟定时把设备叫醒，重渲染并刷屏，屏保时间每 5 分钟跳一次。
- **只在屏保时刷屏**：渲染只写 PNG；只有确认设备确实停在屏保（收到 `goingToScreenSaver` 事件且未收到 `outOfScreenSaver`）时，才用 `eips` 刷 framebuffer，绝不盖住正在阅读的书页。
- **内容每日自动更新**：诗词（今日诗词 jinrishici）+ 英文短句（adviceslip / zenquotes）；抓不到就用本地库轮换，绝不空窗。凌晨 4 点自动临时开 WiFi 抓当天内容，抓完关回去。
- **固定北京时间**：不依赖设备时区设置；农历、干支、节气全部离线计算（Meeus 算法），无外部依赖。
- **双通道 RTC 闹钟 + 看门狗**：rtc1（PMIC alarm1）为主、rtc2（SNVS，独立中断）错开 30 秒兜底；等待期间每 5 秒重写闹钟；唤醒间隔自检（`WAKE-GAP`）一眼定位「闹钟失效」还是「没锁屏」。

## 目录结构

```
kindle-clock/
├── README.md
├── README.en.md                 英文版说明
├── preview.png                  效果图
└── clock/                       ← 整个目录拷到设备的 /mnt/us/clock/
    ├── kindle_clock.py          渲染主程序（758×1024 PNG，农历/干支/节气/诗词排版）
    ├── fetch_daily.py           每日内容抓取（诗词 + 英文短句 → daily.json）
    ├── launch.sh                清醒期循环：渲染 + 抓内容（不刷屏）
    ├── watch_ss.sh              监听进/出屏保事件：锁屏瞬间渲染，维护 /tmp/clock_ss_on 标志
    ├── rtc_refresh.sh           休眠期循环：RTC 闹钟唤醒 + eips 刷屏（唯一刷屏的地方）
    ├── set_alarm.sh             手动设闹钟（调试用，rtc_refresh.sh 已内联同样逻辑）
    ├── install.sh               设备端一键安装（装 upstart 配置并启动三个 job）
    ├── cacert.pem               CA 证书包（越狱设备无系统证书）
    ├── fonts/
    │   ├── NotoSansCJK-RegularSC-sans-sub.otf
    │   └── NotoSerifCJK-RegularSC-serif-sub.otf
    └── init/                    ← 安装时复制到 /etc/init/
        ├── clock_loop.conf      job: clock_loop   → launch.sh
        ├── clock_watch.conf     job: clock_watch  → watch_ss.sh
        └── clock_rtc.conf       job: clock_rtc    → rtc_refresh.sh
```

三个 upstart job 都是 `start on started framework` + `respawn`（5 次/300 秒），开机自启、崩溃自动拉起。

## 工作原理

```
┌─ clock_watch (watch_ss.sh) ── 监听 powerd 事件 ──────────────┐
│   goingToScreenSaver → 建 /tmp/clock_ss_on → 渲染 → eips 刷屏  │
│   outOfScreenSaver   → 删标志（此后任何人都不许再刷屏）          │
└──────────────────────────────────────────────────────────────┘
┌─ clock_loop (launch.sh) ── 清醒期每 60s ─────────────────────┐
│   fetch_daily.py（有网才真抓） → kindle_clock.py（只写 PNG）    │
└──────────────────────────────────────────────────────────────┘
┌─ clock_rtc (rtc_refresh.sh) ── 休眠期每 300s ────────────────┐
│   写 rtc1/rtc2 硬件闹钟 → 设备睡着 → 到点被叫醒                │
│   → 确认还在屏保 → 渲染 + eips 刷屏 → 继续下一轮               │
└──────────────────────────────────────────────────────────────┘
```

关键点：

- **屏保标志 `/tmp/clock_ss_on`**：只有 `watch_ss.sh` 在真正收到事件时才建立/清除。`rtc_refresh.sh` 刷屏前必查这个标志，所以用户阅读时永远不会被刷屏。
- **双通道闹钟**：rtc1（`/sys/class/rtc/rtc1/wakealarm`）写绝对 epoch，但与 powerd 独占的 alarm0 共享中断屏蔽位，偶发被屏蔽；rtc2（`/sys/class/rtc/rtc2/wakealarm`，SNVS，独立电源域/中断）错后 30 秒兜底。rtc2 出厂时间基准是 1970，**每次写闹钟前都会校验基准、偏差 >30s 就用 `hwclock -w --utc` 对表**。
- **等待期每 5 秒重写闹钟**：最后写闹钟的人决定 suspend 时它响不响，勤写把被 powerd 屏蔽的窗口压到最小。
- **凌晨 4 点抓取**：那一轮临时开 WiFi → 抓当日内容 → 按「进来时的状态」关回去；每天只试一次，期间每 5 秒把闹钟推到 now+25s，防止抓到一半被挂起睡死。

## 依赖

| 依赖 | 说明 |
|---|---|
| 越狱 + root | 需要 `mntroot rw` 改 `/etc/init/` |
| Python 3 + Pillow | 设备上 `python3 -c "import PIL"` 能通过 |
| linkss screensaver hack | 提供屏保图机制（只认 `/mnt/us/linkss/screensavers/bg_ssNN.png`） |
| 空闲的 rtc1 / rtc2 | rtc0 被 powerd 独占，不能碰 |
| WiFi 已保存过网络 | 凌晨自动抓取需要设备能自动重连 |

## 安装

### 1. 拷贝文件

USB 连接电脑，把整个 `clock/` 目录拷到 Kindle 用户分区：

```
kindle → /mnt/us/clock/
```

拷完后设备上应有：

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

也可以 SSH 推送：

```sh
ssh root@192.168.x.x "mkdir -p /mnt/us/clock"
scp -r clock/* root@192.168.x.x:/mnt/us/clock/
```

### 2. 设备端安装

SSH 进设备执行（或 KUAL 里进 shell）：

```sh
sh /mnt/us/clock/install.sh
```

脚本会：检查文件完整性 → 检查 Pillow → `mntroot rw` → 复制三个 `.conf` 到 `/etc/init/` → 启动三个 job → 打印状态 → 做一次渲染自检。

### 3. 验证

锁屏一次，屏保应变成时钟图。之后解锁再锁屏，时间应是锁屏那一刻的精确时间。

休眠中每 5 分钟刷新一次需要等一会才能观察到——锁屏后放着，过 10 分钟再点亮看一眼。

## 配置项（环境变量）

均在 `clock/init/*.conf` 里改（改完 `initctl reload-configuration` 并重启对应 job），或运行时 `export`。

### kindle_clock.py

| 变量 | 默认 | 说明 |
|---|---|---|
| `KC_OUT` | `/mnt/us/linkss/screensavers/bg_ss00.png` | 输出 PNG 路径（也接受 argv[1]） |
| `KC_EIPS` | `0` | `1` = 渲染完直接 eips 刷屏 |
| `KC_SLOGAN` | `Take it easy.` | 底部英文兜底句（抓到远程内容时会被覆盖） |
| `KC_DAILY` | `/mnt/us/clock/daily.json` | 每日内容缓存路径 |
| `KC_ROUND5` | `0` | `1` = 时间取整到 5 分钟 |
| `KC_FONT_SANS` / `KC_FONT_SERIF` | `fonts/*.otf` | 无衬线 / 衬线字库路径 |
| `KC_PNG_LEVEL` | `1` | PNG 压缩级别（越大越慢越小） |

### rtc_refresh.sh

| 变量 | 默认 | 说明 |
|---|---|---|
| `KC_RTC` | `1` | 总开关；`0` = 只更新 PNG 不刷屏（省电模式） |
| `KC_RTC_PERIOD` | `300` | 休眠期刷新周期（秒），300 = 对齐整五分 |
| `KC_RTC_DEV` | `/sys/class/rtc/rtc1/wakealarm` | 主通道闹钟 |
| `KC_RTC_DEV2` | `/sys/class/rtc/rtc2/wakealarm` | 备通道闹钟 |
| `KC_NIGHT_FETCH_H` | `04` | 夜间联网抓取的小时（北京时间） |
| `KC_NIGHT_FETCH_WAIT` | `60` | 等 WiFi 上线最多几秒 |

### launch.sh / fetch_daily.py

| 变量 | 默认 | 说明 |
|---|---|---|
| `KC_LOOP_SEC` | `60` | 清醒期渲染周期（秒） |
| `KC_FETCH_FORCE` | `0` | `1` = 强制重新抓取（调试用） |
| `KC_FETCH_TIMEOUT` | `12` | HTTP 超时（秒） |
| `KC_FETCH_RETRY_MIN` | `30` | 抓取失败后的重试间隔（分钟） |

## 日志与排查

| 文件 | 内容 |
|---|---|
| `/tmp/clock_rtc.log` | RTC 循环：`arm target=HH:MM:SS OK <epoch> rtc1 snvs`、`rtc-refresh eips`、`WAKE-GAP`、`NIGHT-FETCH` |
| `/tmp/clock_ss.log` | 屏保事件：`goingToScreenSaver` / `outOfScreenSaver` / `eips repaint` |
| `/tmp/clock_fetch.log` | 内容抓取：`fetch start ...` / `saved poem=...` |
| `/tmp/clock.log` | launch.sh 的 stdout |

常用命令：

```sh
initctl status clock_loop clock_watch clock_rtc   # 三个 job 状态
stop clock_rtc && start clock_rtc                 # 重启 RTC 刷新
python3 /mnt/us/clock/kindle_clock.py             # 手动渲染一次
KC_FETCH_FORCE=1 python3 /mnt/us/clock/fetch_daily.py   # 强制抓内容
sh /mnt/us/clock/set_alarm.sh                     # 手动设一次闹钟，输出 OK <epoch> rtc1 snvs 为正常
grep WAKE-GAP /tmp/clock_rtc.log                  # 出现即说明闹钟曾失效过（正常时应只有历史记录）
tail -f /tmp/clock_rtc.log                        # 看休眠刷新节奏
```

`/tmp` 重启即清空；长期日志在 `/var/log/upstart/clock_*.log`。

## 卸载

```sh
mntroot rw
stop clock_loop; stop clock_watch; stop clock_rtc
rm -f /etc/init/clock_loop.conf /etc/init/clock_watch.conf /etc/init/clock_rtc.conf
initctl reload-configuration
mntroot ro
rm -rf /mnt/us/clock
```

## 已知限制

- **休眠中 SSH 连不上是正常的**：挂起时 WiFi 被 powerd 关闭，设备只被 RTC 闹钟短暂叫醒，SSH 握手来不及完成。要看日志请解锁设备后再连。
- **一整天不解锁**：正常情况下凌晨 4 点会自动联网抓当天内容；若抓取失败（夜间无网/路由器关了），白天解锁后第一次渲染前会自动补抓。
- 屏保图文件名必须是 `bg_ssNN.png`（linkss 约定），想换位置改 `KC_OUT` 即可。

## 字体许可

`fonts/` 下的两个字库是从 Noto Sans/Serif CJK SC 提取并子集化（约 240 字形）的衍生物，遵循 [SIL Open Font License 1.1](https://scripts.sil.org/OFL)。原始字体 © Google / Adobe。

## 许可

代码部分采用 [MIT License](LICENSE)。
