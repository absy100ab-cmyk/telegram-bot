import requests, time, os, json, hashlib, yt_dlp, re

TOKEN = os.environ["TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
os.makedirs("/tmp/dl", exist_ok=True)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

START_MSG = "👋 أهلاً بك!\nأرسل رابط الفيديو للتحميل مباشرةً.\n\n📱 المنصات: يوتيوب | تيك توك | انستغرام | فيسبوك | بنترست\n\n👨‍💻 المالك: @B43lB"
HELP_MSG = "📥 أرسل رابط الفيديو\n🎥 اختر الجودة المناسبة\n🎵 أو اختر تحميل كملف صوتي\n\n👨‍💻 @B43lB"
ABOUT_MSG = "🤖 بوت التحميل v4.6 المستقر\n🔒 آمن وسريع ويعمل بدون توقف\n👨‍💻 @B43lB"
SETTINGS_MSG = "⚙️ الإعدادات الحالية\n📦 حد الملفات: 50MB\n🔐 نظام الكوكيز: مفعّل بنجاح"

def build_cookies():
    cf = "/tmp/dl/cookies.txt"
    with open(cf, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        try:
            for c in json.loads(os.environ.get("YT_COOKIES", "[]")):
                f.write(f"{c.get('domain', '.youtube.com')}\tTRUE\t{c.get('path','/')}\t{'TRUE' if c.get('secure') else 'FALSE'}\t{str(int(c.get('expirationDate', 0))) if c.get('expirationDate') else '0'}\t{c['name']}\t{c['value']}\n")
        except: pass
        try:
            for c in json.loads(os.environ.get("FB_COOKIES", "[]")):
                f.write(f"{c.get('domain', '.facebook.com')}\tTRUE\t{c.get('path','/')}\t{'TRUE' if c.get('secure') else 'FALSE'}\t{str(int(c.get('expirationDate', 0))) if c.get('expirationDate') else '0'}\t{c['name']}\t{c['value']}\n")
        except: pass
    return cf

COOKIES_FILE = build_cookies()

def sm(cid, txt, kb=None):
    try:
        p = {"chat_id": cid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        return session.post(f"{API}/sendMessage", json=p, timeout=5)
    except: return None

def em(cid, mid, txt, kb=None):
    try:
        p = {"chat_id": cid, "message_id": mid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/editMessageText", json=p, timeout=5)
    except: pass

def ac(qid, txt, alert=False):
    try: session.post(f"{API}/answerCallbackQuery", json={"callback_query_id": qid, "text": txt, "show_alert": alert}, timeout=2)
    except: pass

def fb_fallback(url):
    try:
        res = session.get(url, timeout=15, allow_redirects=True)
        html = res.text
        links = re.findall(r'"playable_url(?:_quality_hd)?":"([^"]+)"', html)
        if not links: links = re.findall(r'"[sh]d_src":"([^"]+)"', html)
        if links:
            vurl = links[0].replace(r'\/', '/').replace(r'\u0025', '%')
            if '\\u' in vurl:
                try: vurl = vurl.encode().decode('unicode_escape')
                except: pass
            path = f"/tmp/dl/fb_{int(time.time())}.mp4"
            vr = session.get(vurl, stream=True, timeout=60)
            with open(path, 'wb') as f:
                for ch in vr.iter_content(1024*1024):
                    if ch: f.write(ch)
            return path, "فيديو فيسبوك (نظام الإنقاذ)"
    except: pass
    return None, None

def dl(url, quality="480", is_video=True, is_playlist=False):
    if is_playlist:
        try:
            with yt_dlp.YoutubeDL({'extract_flat': True, 'playlistend': 50, 'quiet': True, 'cookiefile': COOKIES_FILE}) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info or 'entries' not in info: return None, "قائمة فارغة"
            return "PLAYLIST_DATA", info['entries']
        except Exception as e: return None, str(e)[:200]

    if is_video:
        fmt = f"best[height<={quality}][hasaudio]/best[height<={quality}]/best"
    else:
        fmt = "bestaudio/best"

    opts = {
        'outtmpl': '/tmp/dl/%(title).50s.%(ext)s',
        'format': fmt,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'retries': 5,
        'socket_timeout': 60,
        'cookiefile': COOKIES_FILE,
        'user_agent': 'Mozilla/5.0',
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info: return None, "فشل التحميل"
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            for ext in ['mp4','mkv','webm','m4a','mp3']:
                if os.path.exists(f"{base}.{ext}"):
                    path = f"{base}.{ext}"
                    break
        if os.path.exists(path): return path, info.get('title', 'فيديو')
        return None, "الملف غير موجود"
    except Exception as e:
        if is_video and ("facebook.com" in url.lower() or "fb.watch" in url.lower()):
            f_path, f_title = fb_fallback(url)
            if f_path and os.path.exists(f_path): return f_path, f_title
        err = str(e)
        if "private" in err.lower(): return None, "المحتوى خاص"
        if "login" in err.lower(): return None, "يتطلب كوكيز"
        return None, err[:200]

def save_urls():
    try:
        with open('/tmp/dl/urls.json', 'w') as f: json.dump(urls, f)
    except: pass

def load_urls():
    global urls
    try:
        with open('/tmp/dl/urls.json', 'r') as f: urls = json.load(f)
    except: urls = {}

def process(u):
    if "callback_query" in u:
        q = u["callback_query"]
        cid = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        d = q["data"]
        if d.startswith("q_"):
            parts = d.split("_")
            key = parts[1]
            quality = parts[2]
            if key not in urls:
                ac(q["id"], "انتهت الجلسة", True)
                return
            url = urls[key]
            is_pl = "playlist" in url.lower() or "list=" in url.lower()
            ac(q["id"], "تجهيز الطلب...")
            if is_pl:
                em(cid, mid, "⏳ جاري فحص قائمة التشغيل...")
                status, entries = dl(url, quality, True, is_playlist=True)
                if status == "PLAYLIST_DATA":
                    total = len(entries)
                    em(cid, mid, f"📋 تحتوي على {total} فيديو.\n⏳ جاري التحميل...")
                    for idx, entry in enumerate(entries, 1):
                        v_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                        em(cid, mid, f"⏳ جاري معالجة [{idx}/{total}]:\n{entry.get('title', 'بدون عنوان')}")
                        v_path, v_title = dl(v_url, quality, True, is_playlist=False)
                        if v_path and os.path.exists(v_path):
                            v_size = os.path.getsize(v_path)//(1024*1024)
                            if v_size <= 50:
                                try:
                                    with open(v_path, 'rb') as f:
                                        session.post(f"{API}/sendVideo", data={"chat_id": cid, "supports_streaming": True, "caption": f"🎬 [{idx}/{total}] {v_title}\n📦 {v_size}MB"}, files={"video": f}, timeout=300)
                                except: pass
                            try: os.remove(v_path)
                            except: pass
                    em(cid, mid, f"✅ اكتمل تحميل القائمة ({total} فيديو) بنجاح!")
                else: em(cid, mid, f"❌ {entries}")
            else:
                em(cid, mid, f"⏳ جاري تحميل الفيديو بجودة {quality}p...")
                path, title = dl(url, quality, True, is_playlist=False)
                if path and os.path.exists(path):
                    size = os.path.getsize(path)//(1024*1024)
                    if size > 50: em(cid, mid, f"⚠️ كبير ({size}MB)\nجرب جودة أقل")
                    else:
                        try:
                            with open(path,'rb') as f:
                                session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"✅ {title}\n📦 {size}MB"}, files={"video":f}, timeout=300)
                            em(cid, mid, f"✅ {title}")
                        except: em(cid, mid, "فشل الإرسال")
                    try: os.remove(path)
                    except: pass
                else: em(cid, mid, f"❌ {title}")
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls:
                ac(q["id"], "انتهت الجلسة", True)
                return
            ac(q["id"], "تحميل صوت...")
            em(cid, mid, "⏳ تحميل الصوت...")
            path, title = dl(urls[key], "480", False)
            if path and os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        session.post(f"{API}/sendAudio", data={"chat_id":cid,"caption":f"🎵 {title}"}, files={"audio":f}, timeout=300)
                    em(cid, mid, f"✅ {title}")
                except: em(cid, mid, "فشل الإرسال")
                try: os.remove(path)
                except: pass
            else: em(cid, mid, f"❌ {title}")
    if "message" in u and "text" in u["message"]:
        m = u["message"]
        cid = m["chat"]["id"]
        txt = m["text"].strip()
        if txt == "/start": sm(cid, START_MSG)
        elif txt == "/help": sm(cid, HELP_MSG)
        elif txt == "/about": sm(cid, ABOUT_MSG)
        elif txt == "/settings": sm(cid, SETTINGS_MSG)
        elif txt.startswith("http"):
            key = hashlib.md5(txt.encode()).hexdigest()[:8]
            urls[key] = txt
            save_urls()
            is_pl = "playlist" in txt.lower() or "list=" in txt.lower()
            kb = json.dumps({"inline_keyboard": [
                [{"text": "🎥 144p", "callback_data": f"q_{key}_144"}, {"text": "🎥 360p", "callback_data": f"q_{key}_360"}],
                [{"text": "🎥 480p", "callback_data": f"q_{key}_480"}, {"text": "🎥 720p", "callback_data": f"q_{key}_720"}],
                [{"text": "🎥 1080p", "callback_data": f"q_{key}_1080"}],
                [{"text": "🎵 صوت", "callback_data": f"a_{key}"}]
            ]})
            msg = "✅ **تم استلام الرابط**"
            if is_pl: msg += "\n📋 **تم اكتشاف قائمة تشغيل!**"
            msg += "\n\n**اختر الجودة أو الصوت:**"
            sm(cid, msg, kb)

def run():
    global offset
    load_urls()
    print("⚡ البوت يعمل بكفاءة قصوى...")
    while True:
        try:
            r = session.get(f"{API}/getUpdates", params={"offset":offset+1,"timeout":15}, timeout=20)
            if r.status_code != 200:
                time.sleep(2)
                continue
            for u in r.json().get("result", []):
                offset = u["update_id"]
                process(u)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run()
