#!/usr/bin/env python3

import json, os, ssl, sys, time, subprocess, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kindle_clock as kc

DAILY = os.environ.get("KC_DAILY", "/mnt/us/clock/daily.json")
START_H = int(os.environ.get("KC_FETCH_START", "1"))
WINDOW_MIN = int(os.environ.get("KC_FETCH_WINDOW", "20"))
FORCE = os.environ.get("KC_FETCH_FORCE", "0") == "1"
TIMEOUT = int(os.environ.get("KC_FETCH_TIMEOUT", "12"))
RETRY_MIN = int(os.environ.get("KC_FETCH_RETRY_MIN", "30"))
LOCK = os.environ.get("KC_FETCH_LOCK", "/tmp/clock_fetch.lock")
LOCK_MAX_AGE = 900

POEM_URL = "https://v1.jinrishici.com/all.json"
ADVICE_URL = "https://api.adviceslip.com/advice"
QUOTE_URL = "https://zenquotes.io/api/random"

MAX_POEM_LEN = 17
MAX_QUOTE_LEN = 42
MAX_QUOTE_LEN2 = 60
LOG = os.environ.get("KC_FETCH_LOG", "/tmp/clock_fetch.log")

def log(msg):
    line = ">> %s %s" % (kc.now_cn().strftime("%m-%d %H:%M:%S"), msg)
    print(line)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def ssl_ctx():
    cafile = "/mnt/us/clock/cacert.pem"
    if os.path.exists(cafile):
        return ssl.create_default_context(cafile=cafile)
    return ssl._create_unverified_context()

def fetch_json(url, tries=3, gap=3.0):
    last = ""
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT, context=ssl_ctx()) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as ex:
            last = "%s: %s" % (type(ex).__name__, str(ex)[:60])
            if i + 1 < tries:
                time.sleep(gap)
    log("fetch fail %s (%s)" % (url.split("/")[2], last))
    return None

def renderable(text):
    return not kc.missing_glyphs(text, serif=True) and not kc.missing_glyphs(text, serif=False)

def clean_poem(d):
    if not isinstance(d, dict) or not d.get("content"):
        return None
    line = d["content"].strip().rstrip("。").strip()
    if len(line) > MAX_POEM_LEN or "，" not in line and "、" not in line and len(line) < 8:
        return None
    author = (d.get("author") or "").strip()
    title = (d.get("origin") or "").strip()
    full = line + "——" + author + "《" + title + "》"
    if not renderable(full):
        log("poem dropped (glyph): %s" % line)
        return None
    if len(line) > MAX_POEM_LEN:
        return None
    return {"line": line, "title": title, "author": author}

def clean_quote(text):
    if not text:
        return None
    s = " ".join(text.split())
    if not s or len(s) > MAX_QUOTE_LEN:
        return None
    if any(ord(c) > 126 or ord(c) < 32 for c in s):
        return None
    if not renderable(s):
        log("quote dropped (glyph): %s" % s[:30])
        return None
    return s

def get_poem():
    for _ in range(3):
        d = fetch_json(POEM_URL, tries=2, gap=3.0)
        p = clean_poem(d) if d else None
        if p:
            return p, "jinrishici"
    return None, None

def get_quote():
    for _ in range(6):
        d = fetch_json(ADVICE_URL, tries=1)
        if d:
            q = clean_quote((d.get("slip") or {}).get("advice"))
            if q:
                return q, "adviceslip"
        time.sleep(1.0)

    for _ in range(2):
        d = fetch_json(QUOTE_URL, tries=1)
        if d and isinstance(d, list) and d:
            s = " ".join((d[0].get("q") or "").split())
            if s and len(s) <= MAX_QUOTE_LEN2 and all(32 <= ord(c) <= 126 for c in s) and renderable(s):
                return s, "zenquotes"
        time.sleep(3.0)
    return None, None

def load():
    try:
        with open(DAILY) as f:
            return json.load(f)
    except Exception:
        return {}

def save_atomic(data):
    tmp = "%s.%d.tmp" % (DAILY, os.getpid())
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DAILY)

def have_net():
    try:
        out = subprocess.check_output(["lipc-get-prop", "com.lab126.wifid", "cmState"],
                                      stderr=subprocess.STDOUT, timeout=6).decode("utf-8", "replace")
        s = out.strip().upper()
        if "CONNECTED" in s:
            return True
        if s and "FAILED" not in s:
            return False
    except Exception:
        pass
    try:
        with open("/proc/net/route") as f:
            for line in f.read().splitlines()[1:]:
                p = line.split()
                if len(p) > 3 and p[1] == "00000000" and int(p[3], 16) & 2:
                    return True
    except Exception:
        pass
    return False

def lock_acquire():
    try:
        if time.time() - os.stat(LOCK).st_mtime > LOCK_MAX_AGE:
            os.remove(LOCK)
    except OSError:
        pass
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, ("%d" % os.getpid()).encode())
        os.close(fd)
        return True
    except OSError:
        return False

def lock_release():
    try:
        os.remove(LOCK)
    except OSError:
        pass

def done_today(cur, today):
    return cur.get("date") == today and bool(cur.get("ok_poem")) and bool(cur.get("ok_slogan"))

def tried_too_soon(cur):
    prev = cur.get("last_try_ts")
    if not isinstance(prev, (int, float)):
        return False
    return (time.time() - float(prev)) < RETRY_MIN * 60

def main():
    now = kc.now_cn()
    today = now.date().isoformat()
    cur = load()

    if not FORCE:
        if done_today(cur, today):
            return 0
        if tried_too_soon(cur):
            return 0
        if not have_net():
            return 0

    if not lock_acquire():
        return 0
    try:
        cur = load()
        if not FORCE and done_today(cur, today):
            return 0

        log("fetch start (force=%d) last_ok=%s missing=%s%s" % (
            FORCE, cur.get("date"),
            "" if cur.get("ok_poem") else "poem ",
            "" if cur.get("ok_slogan") else "slogan"))

        poem, psrc = get_poem()
        quote, qsrc = get_quote()

        data = dict(cur)
        data["last_try_ts"] = int(time.time())
        if poem:
            data["poem"] = poem
            data["poem_src"] = psrc
        if quote:
            data["slogan"] = quote
            data["slogan_src"] = qsrc
        if poem or quote:
            data["date"] = today
            data["ts"] = now.isoformat(timespec="seconds")
            data["ok_poem"] = bool(poem)
            data["ok_slogan"] = bool(quote)
        else:
            data["ok_poem"] = False
            data["ok_slogan"] = False

        try:
            save_atomic(data)
        except Exception as ex:
            log("SAVE FAIL %s" % ex)
            return 1

        log("saved poem=%s(%s) slogan=%r(%s)" % (
            (poem or {}).get("line"), psrc or "-", quote, qsrc or "-"))
        return 0 if (poem or quote) else 1
    finally:
        lock_release()

if __name__ == "__main__":
    sys.exit(main())
