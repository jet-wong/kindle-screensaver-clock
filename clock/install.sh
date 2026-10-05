#!/bin/sh
set -u
D=/mnt/us/clock

echo "== kindle-clock 安装 =="

[ -d "$D/init" ] || { echo "!! 缺少 $D/init （clock_loop.conf / clock_watch.conf / clock_rtc.conf 应在里面）"; exit 1; }

for f in kindle_clock.py fetch_daily.py launch.sh watch_ss.sh rtc_refresh.sh set_alarm.sh cacert.pem; do
    [ -f "$D/$f" ] || { echo "!! 缺少 $D/$f"; exit 1; }
done
[ -f "$D/fonts/NotoSansCJK-RegularSC-sans-sub.otf" ] || { echo "!! 缺少正文字库 fonts/NotoSansCJK-RegularSC-sans-sub.otf"; exit 1; }
[ -f "$D/fonts/NotoSerifCJK-RegularSC-serif-sub.otf" ] || { echo "!! 缺少衬线字库 fonts/NotoSerifCJK-RegularSC-serif-sub.otf"; exit 1; }

python3 -c "import PIL" 2>/dev/null || echo "!! 警告：python3 缺少 Pillow，渲染会失败（KUAL 里装 KUAL/Pillow 或 pip install Pillow）"

chmod 755 "$D"/*.sh 2>/dev/null

echo "-> mntroot rw （挂载根分区可写）"
mntroot rw || { echo "!! mntroot rw 失败，确认设备已越狱且当前是 root"; exit 1; }

cp "$D/init/clock_loop.conf"  /etc/init/ || exit 1
cp "$D/init/clock_watch.conf" /etc/init/ || exit 1
cp "$D/init/clock_rtc.conf"   /etc/init/ || exit 1
echo "-> 三个 .conf 已复制到 /etc/init/"

initctl reload-configuration
for j in clock_loop clock_watch clock_rtc; do
    stop $j >/dev/null 2>&1
    start $j >/dev/null 2>&1
done
sleep 2
echo "-> job 状态："
initctl status clock_loop
initctl status clock_watch
initctl status clock_rtc

mntroot ro >/dev/null 2>&1
mkdir -p /mnt/us/linkss/screensavers

echo
echo "安装完成。首次渲染自检："
python3 "$D/kindle_clock.py"
echo "若上面打印了 rendered ... 且生成了 /mnt/us/linkss/screensavers/bg_ss00.png 即为成功。"
echo "锁屏一次看屏保是否变成时钟；若没变，检查 linkss 是否已装：ls /mnt/us/linkss/"
