#!/usr/bin/env python3

import os, sys, math, json, datetime, subprocess

from PIL import Image, ImageDraw, ImageFont

TZ_CN = datetime.timezone(datetime.timedelta(hours=8), "Asia/Shanghai")
def now_cn():
    return datetime.datetime.now(TZ_CN)

W, H = 758, 1024
M = 60
SLOGAN = os.environ.get("KC_SLOGAN", "Take it easy.")

SLOGANS = ["Take it easy.", "Easy does it.", "Let it be.", "Keep it simple.",
           "Slow and steady.", "One step at a time.", "So far, so good."]

DAILY = os.environ.get("KC_DAILY", "/mnt/us/clock/daily.json")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "KC_OUT", "/mnt/us/linkss/screensavers/bg_ss00.png")
DO_EIPS = os.environ.get("KC_EIPS", "0") == "1"

FONT_SANS = os.environ.get("KC_FONT_SANS", "/mnt/us/clock/fonts/NotoSansCJK-RegularSC-sans-sub.otf")
FONT_SERIF = os.environ.get("KC_FONT_SERIF", "/mnt/us/clock/fonts/NotoSerifCJK-RegularSC-serif-sub.otf")

BG, INK, GRAY, FAINT, LINE, TRACK = 245, 22, 85, 150, 170, 215

S_TIME   = 180
S_DATE   = 26
S_LUNAR  = 24
S_TERM   = 56
S_TERMD  = 24
S_TERM2  = 42
S_TERMD2 = 20
S_SUB    = 22
S_POEM   = 38
S_SLOGAN = 30

Y_TIME   = 207
Y_DATE   = 325
Y_LUNAR  = 364
Y_SEP1   = 421
Y_TERM   = 492
Y_TERMD  = 553
Y_SEP2   = 623
Y_POEM   = 706
Y_FROM   = 767
Y_SLOGAN = 871
TERM_DX  = 145

POEMS = [
    {"title": "月夜忆舍弟", "author": "杜甫",  "lines": ["露从今夜白", "月是故乡明"]},
    {"title": "山居秋暝",   "author": "王维",  "lines": ["空山新雨后", "天气晚来秋"]},
    {"title": "秋词",       "author": "刘禹锡", "lines": ["自古逢秋悲寂寥", "我言秋日胜春朝"]},
    {"title": "枫桥夜泊",   "author": "张继",  "lines": ["月落乌啼霜满天", "江枫渔火对愁眠"]},
    {"title": "天净沙·秋思", "author": "马致远", "lines": ["枯藤老树昏鸦", "小桥流水人家"]},
    {"title": "登高",       "author": "杜甫",  "lines": ["无边落木萧萧下", "不尽长江滚滚来"]},
    {"title": "十五夜望月", "author": "王建",  "lines": ["中庭地白树栖鸦", "冷露无声湿桂花"]},
    {"title": "夜雨寄北",   "author": "李商隐", "lines": ["君问归期未有期", "巴山夜雨涨秋池"]},
    {"title": "秋夕",       "author": "杜牧",  "lines": ["银烛秋光冷画屏", "轻罗小扇扑流萤"]},
]
POEM_PERIOD_H = 4

WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

LUNAR_DATA = [
0x04bd8,0x04ae0,0x0a570,0x054d5,0x0d260,0x0d950,0x16554,0x056a0,0x09ad0,0x055d2,
0x04ae0,0x0a5b6,0x0a4d0,0x0d250,0x1d255,0x0b540,0x0d6a0,0x0ada2,0x095b0,0x14977,
0x04970,0x0a4b0,0x0b4b5,0x06a50,0x06d40,0x1ab54,0x02b60,0x09570,0x052f2,0x04970,
0x06566,0x0d4a0,0x0ea50,0x06e95,0x05ad0,0x02b60,0x186e3,0x092e0,0x1c8d7,0x0c950,
0x0d4a0,0x1d8a6,0x0b550,0x056a0,0x1a5b4,0x025d0,0x092d0,0x0d2b2,0x0a950,0x0b557,
0x06ca0,0x0b550,0x15355,0x04da0,0x0a5b0,0x14573,0x052b0,0x0a9a8,0x0e950,0x06aa0,
0x0aea6,0x0ab50,0x04b60,0x0aae4,0x0a570,0x05260,0x0f263,0x0d950,0x05b57,0x056a0,
0x096d0,0x04dd5,0x04ad0,0x0a4d0,0x0d4d4,0x0d250,0x0d558,0x0b540,0x0b5a0,0x195a6,
0x095b0,0x049b0,0x0a974,0x0a4b0,0x0b27a,0x06a50,0x06d40,0x0af46,0x0ab60,0x09570,
0x04af5,0x04970,0x064b0,0x074a3,0x0ea50,0x06b58,0x05ac0,0x0ab60,0x096d5,0x092e0,
0x0c960,0x0d954,0x0d4a0,0x0da50,0x07552,0x056a0,0x0abb7,0x025d0,0x092d0,0x0cab5,
0x0a950,0x0b4a0,0x0baa4,0x0ad50,0x055d9,0x04ba0,0x0a5b0,0x15176,0x052b0,0x0a930,
0x07954,0x06aa0,0x0ad50,0x05b52,0x04b60,0x0a6e6,0x0a4e0,0x0d260,0x0ea65,0x0d530,
0x05aa0,0x076a3,0x096d0,0x04bd7,0x04ad0,0x0a4d0,0x1d0b6,0x0d250,0x0d520,0x0dd45,
0x0b5a0,0x056d0,0x055b2,0x049b0,0x0a577,0x0a4b0,0x0aa50,0x1b255,0x06d20,0x0ada0,
0x14b63,0x09370,0x049f8,0x04970,0x064b0,0x168a6,0x0ea50,0x06b20,0x1a6c4,0x0aae0,
0x0a2e0,0x0d2e3,0x0c960,0x0d557,0x0d4a0,0x0da50,0x05d55,0x056a0,0x0a6d0,0x055d4,
0x052d0,0x0a9b8,0x0a950,0x0b4a0,0x0b6a6,0x0ad50,0x055a0,0x0aba4,0x0a5b0,0x052b0,
0x0b273,0x06930,0x07337,0x06aa0,0x0ad50,0x14b55,0x04b60,0x0a570,0x054e4,0x0d160,
0x0e968,0x0d520,0x0daa0,0x16aa6,0x056d0,0x04ae0,0x0a9d4,0x0a2d0,0x0d150,0x0f252,
0x0d520
]
LUNAR_DAY = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
             "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
             "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]
LUNAR_MON = ["正月","二月","三月","四月","五月","六月","七月","八月","九月","十月","十一月","腊月"]
GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

def _lunar_year_days(y):
    s, i = 348, 0x8000
    while i > 0x8:
        if LUNAR_DATA[y - 1900] & i:
            s += 1
        i >>= 1
    return s + _lunar_leap_days(y)

def _lunar_leap_month(y):
    return LUNAR_DATA[y - 1900] & 0xf

def _lunar_leap_days(y):
    return (30 if (LUNAR_DATA[y - 1900] & 0x10000) else 29) if _lunar_leap_month(y) else 0

def _lunar_month_days(y, m):
    return 30 if (LUNAR_DATA[y - 1900] & (0x10000 >> m)) else 29

def solar_to_lunar(date):
    offset = (date - datetime.date(1900, 1, 31)).days
    i, temp = 1900, 0
    while i < 2101 and offset > 0:
        temp = _lunar_year_days(i)
        offset -= temp
        i += 1
    if offset < 0:
        offset += temp
        i -= 1
    ly = i
    leap, is_leap = _lunar_leap_month(ly), False
    i = 1
    while i < 13 and offset > 0:
        if leap > 0 and i == leap + 1 and not is_leap:
            i -= 1
            is_leap = True
            temp = _lunar_leap_days(ly)
        else:
            temp = _lunar_month_days(ly, i)
        if is_leap and i == leap + 1:
            is_leap = False
        offset -= temp
        i += 1
    if offset == 0 and leap > 0 and i == leap + 1:
        if is_leap:
            is_leap = False
        else:
            is_leap = True
            i -= 1
    if offset < 0:
        offset += temp
        i -= 1
    return ly, i, offset + 1, is_leap

def ganzhi_year(ly):
    return GAN[(ly - 1984) % 10] + ZHI[(ly - 1984) % 12] + "年"

def lunar_str(date):
    ly, lm, ld, is_leap = solar_to_lunar(date)
    mon = ("闰" if is_leap else "") + LUNAR_MON[lm - 1]
    return "农历%s%s · %s" % (mon, LUNAR_DAY[ld - 1], ganzhi_year(ly))

TERM_LON = [
    ("春分",0),("清明",15),("谷雨",30),("立夏",45),("小满",60),("芒种",75),
    ("夏至",90),("小暑",105),("大暑",120),("立秋",135),("处暑",150),("白露",165),
    ("秋分",180),("寒露",195),("霜降",210),("立冬",225),("小雪",240),("大雪",255),
    ("冬至",270),("小寒",285),("大寒",300),("立春",315),("雨水",330),("惊蛰",345),
]
TERM_LON_D = dict(TERM_LON)

def _jd(dt):
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1; m += 12
    A = y // 100
    B = 2 - A + A // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

def _sun_lon(jd):
    T = (jd - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360
    Mr = math.radians(M)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(Mr)
         + (0.019993 - 0.000101 * T) * math.sin(2 * Mr)
         + 0.000289 * math.sin(3 * Mr))
    om = math.radians(125.04 - 1934.136 * T)
    return (L0 + C - 0.00569 - 0.00478 * math.sin(om)) % 360

def _term_instant(year, lon):
    def diff(x):
        return ((_sun_lon(x) - lon + 180.0) % 360.0) - 180.0
    x = _jd(datetime.datetime(year, 1, 1))
    d0 = diff(x)
    while x < _jd(datetime.datetime(year + 1, 2, 1)):
        x2 = x + 5.0
        d1 = diff(x2)
        if d0 <= 0 < d1:
            a, b = x, x2
            for _ in range(40):
                m = (a + b) / 2
                if diff(m) <= 0:
                    a = m
                else:
                    b = m
            return (a + b) / 2
        x, d0 = x2, d1
    return None

def _term_date(year, name):
    jd = _term_instant(year, TERM_LON_D[name])
    dt = datetime.datetime(2000, 1, 1, 12) + datetime.timedelta(days=jd - 2451545.0 + 8 / 24.0)
    return dt.date()

_BASE = {}
_NODEF = {}

def _base(serif):
    key = "serif" if serif else "sans"
    if key not in _BASE:
        _BASE[key] = ImageFont.truetype(FONT_SERIF if serif else FONT_SANS, 32)
        try:
            _NODEF[key] = _BASE[key].getmask("\ue123").getbbox()
        except Exception:
            _NODEF[key] = None
    return _BASE[key]

def F(sz, serif=False):
    b = _base(serif)
    return b if b.size == sz else b.font_variant(size=sz)

def missing_glyphs(text, serif=True):
    b = _base(serif)
    ref = _NODEF.get("serif" if serif else "sans")
    out = []
    for ch in text:
        if ch.isspace():
            continue
        try:
            box = b.font_variant(size=32).getmask(ch).getbbox()
        except Exception:
            out.append(ch)
            continue
        if box is None or (ref is not None and box == ref):
            out.append(ch)
    return out

def ct(d, xy, t, f, fill, anc="mm"):
    d.text(xy, t, font=f, fill=fill, anchor=anc)

def text_w(d, t, f):
    try:
        return d.textlength(t, font=f)
    except Exception:
        try:
            return f.getlength(t)
        except Exception:
            return d.textsize(t, font=f)[0]

def fit_font(d, t, size, max_w, serif=True, min_sz=26):
    f = F(size, serif)
    while size > min_sz and text_w(d, t, f) > max_w:
        size -= 2
        f = F(size, serif)
    return f

def hl(d, y, x0=None, x1=None, fill=LINE, w=2):
    d.line([(x0 if x0 is not None else M, y), (x1 if x1 is not None else W - M, y)], fill=fill, width=w)

def clock_str():
    n = now_cn()
    mm = n.minute
    if os.environ.get("KC_ROUND5", "0") == "1":
        mm = (mm // 5) * 5
    return "%02d:%02d" % (n.hour, mm)

def load_daily(today):
    try:
        with open(DAILY) as f:
            d = json.load(f)
        return d if isinstance(d, dict) and d.get("date") == today.isoformat() else None
    except Exception:
        return None

def pick_poem(now, daily=None):
    d = daily or {}
    p = d.get("poem")
    if isinstance(p, dict) and p.get("line") and not missing_glyphs(p["line"] + (p.get("title") or "")
                                                                    + (p.get("author") or "")):
        return {"line": p["line"], "title": p.get("title", ""), "author": p.get("author", ""),
                "src": d.get("poem_src", "net")}
    slot = now.timetuple().tm_yday * (24 // POEM_PERIOD_H) + (now.hour // POEM_PERIOD_H)
    p = POEMS[slot % len(POEMS)]
    return {"line": "，".join(p["lines"]), "title": p["title"], "author": p["author"], "src": "local"}

def pick_slogan(today, daily=None):
    d = daily or {}
    s = d.get("slogan")
    if isinstance(s, str) and s and not missing_glyphs(s):
        return s
    if SLOGAN and SLOGAN != "Take it easy.":
        return SLOGAN
    return SLOGANS[today.toordinal() % len(SLOGANS)]

def term_cycle(today):
    dates = {}
    for name, _ in TERM_LON:
        dates[name] = min((_term_date(y, name) for y in (today.year - 1, today.year, today.year + 1)),
                          key=lambda d: abs((d - today).days))
    past = {n: d for n, d in dates.items() if d <= today}
    fut = {n: d for n, d in dates.items() if d > today}
    cur = max(past, key=lambda n: past[n])
    nxt = min(fut, key=lambda n: fut[n])
    span = (dates[nxt] - dates[cur]).days
    pct = max(0, min(100, int(round((today - dates[cur]).days / span * 100)))) if span > 0 else 0
    return {"dates": dates, "cur": cur, "cur_dt": dates[cur], "next": nxt, "next_dt": dates[nxt],
            "days": (dates[nxt] - today).days, "pct": pct}

def term_near(cyc, today):
    return "next" if (cyc["next_dt"] - today).days <= (today - cyc["cur_dt"]).days else "cur"

def draw_two_terms(d, cyc, today):
    cx = W / 2
    xl, xr = cx - TERM_DX, cx + TERM_DX
    near = term_near(cyc, today)
    for x, key in ((xl, "cur"), (xr, "next")):
        is_near = (key == near)
        dt = cyc["cur_dt"] if key == "cur" else cyc["next_dt"]
        ct(d, (x, Y_TERM), cyc[key], F(S_TERM if is_near else S_TERM2, serif=True),
           INK if is_near else GRAY)
        ct(d, (x, Y_TERMD), "%d月%d日" % (dt.month, dt.day),
           F(S_TERMD if is_near else S_TERMD2), GRAY if is_near else FAINT)

def render(clk, today, cyc, poem, lunar, slogan=None):
    img = Image.new("L", (W, H), BG)
    d = ImageDraw.Draw(img)
    wk = WD[today.weekday()]
    slogan = slogan or pick_slogan(today)

    ct(d, (W / 2, Y_TIME), clk, F(S_TIME, serif=True), INK)

    ct(d, (W / 2, Y_DATE), "%d年%d月%d日 · %s" % (today.year, today.month, today.day, wk), F(S_DATE), GRAY)
    ct(d, (W / 2, Y_LUNAR), lunar, F(S_LUNAR), GRAY)
    hl(d, Y_SEP1)

    draw_two_terms(d, cyc, today)
    hl(d, Y_SEP2)

    line = poem["line"]
    ct(d, (W / 2, Y_POEM), line, fit_font(d, line, S_POEM, W - 2 * M, serif=True), INK)
    ct(d, (W / 2, Y_FROM), "—— %s《%s》" % (poem["author"], poem["title"]), F(S_SUB), GRAY)

    ct(d, (W / 2, Y_SLOGAN), slogan, fit_font(d, slogan, S_SLOGAN, W - 2 * M, serif=False, min_sz=18),
       GRAY)

    tmp = "%s.%d.tmp" % (OUT, os.getpid())
    try:
        img.save(tmp, "PNG", compress_level=int(os.environ.get("KC_PNG_LEVEL", "1")))
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
    return img

def main():
    now = now_cn()
    today = now.date()
    cyc = term_cycle(today)
    daily = load_daily(today)
    poem = pick_poem(now, daily)
    slogan = pick_slogan(today, daily)
    lunar = lunar_str(today)
    render(clock_str(), today, cyc, poem, lunar, slogan)
    if DO_EIPS:
        subprocess.run(["eips", "-f", "-g", OUT])
    print("rendered %s | cur=%s(%s) next=%s(%s) in %dd pct=%d%% near=%s | poem=%s/%s | slogan=%r/%s" % (
        OUT, cyc["cur"], cyc["cur_dt"], cyc["next"], cyc["next_dt"], cyc["days"], cyc["pct"],
        term_near(cyc, today), poem["title"], poem.get("src"),
        slogan, (daily or {}).get("slogan_src", "local")))

CHARS = set("0123456789:%·—《》%还有天就在今日月日")
CHARS |= set("".join(WD))
CHARS |= set("".join(LUNAR_DAY) + "".join(LUNAR_MON) + "".join(GAN) + "".join(ZHI) + "农历闰年月")
CHARS |= set("".join(n for n, _ in TERM_LON))
CHARS |= set("".join("".join(p["lines"]) + p["title"] + p["author"] for p in POEMS))
CHARS |= set(SLOGAN)

if __name__ == "__main__":
    main()
