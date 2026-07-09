import requests
import time
import os
import json
import hashlib
import yt_dlp

TOKEN = os.environ["TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
os.makedirs("/tmp/dl", exist_ok=True)
session = requests.Session()
session.headers.update({"Connection": "keep-alive", "User-Agent": "Mozilla/5.0"})

START_MSG = """👋 أهلاً بك!
📩 أرسل رابط الوسيط الذي ترغب بإدارته أو مشاركته.

📌 يرجى التأكد من أن لديك الحق الكامل لاستخدام الرابط المُرسل.

✅ جاهز؟ فقط أرسل الرابط لبدء المعالجة.

📱 المنصات: يوتيوب | تيك توك | انستغرام | تويتر | فيسبوك | سناب | بنترست

المالك ✓ @B43lB"""

HELP_MSG = """🆘 **المساعدة**
📥 أرسل رابط الفيديو
🎥 اختر الجودة (144p-1080p)
🎵 أو اختر صوت
📋 أرسل رابط قائمة تشغيل

⚡ /start | /help | /about | /settings
👨‍💻 @B43lB"""

ABOUT_MSG = """🤖 **بوت التحميل v4.0**
📥 يوتيوب - تيك توك - انستغرام
🐦 تويتر - فيسبوك - سناب شات
📌 بنترست - 📋 قوائم التشغيل
🎥 144p إلى 1080p
🎵 تحميل صوت سريع
🔒 آمن - مشفر - 24 ساعة
👨‍💻 @B43lB"""

SETTINGS_MSG = """⚙️ **الإعدادات v4.0**
🎥 الجودة: 144p - 1080p
🎵 الصوت: جودة أصلية
📦 الحد: 50MB
📋 قوائم التشغيل: حتى 50 فيديو
🔐 كوكيز يوتيوب ✅ فيسبوك ✅ تويتر ✅"""

def build_cookies():
    cookie_file = "/tmp/dl/cookies.txt"
    with open(cookie_file, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        
        # يوتيوب
        yt = os.environ.get("YT_COOKIES", "[]")
        try:
            for c in json.loads(yt):
                domain = c.get("domain", ".youtube.com")
                secure = "TRUE" if c.get("secure") else "FALSE"
                http = "TRUE" if c.get("httpOnly") else "FALSE"
                exp = str(int(c.get("expirationDate", 0))) if c.get("expirationDate") else "0"
                f.write(f"{domain}\tTRUE\t{c.get('path','/')}\t{secure}\t{exp}\t{c['name']}\t{c['value']}\n")
        except: pass
        
        # فيسبوك
        fb = os.environ.get("FB_COOKIES", "[]")
        try:
            for c in json.loads(fb):
                domain = c.get("domain", ".facebook.com")
                secure = "TRUE" if c.get("secure") else "FALSE"
                exp = str(int(c.get("expirationDate", 0))) if c.get("expirationDate") else "0"
                f.write(f"{domain}\tTRUE\t{c.get('path','/')}\t{secure}\t{exp}\t{c['name']}\t{c['value']}\n")
        except: pass
        
        # تويتر
        tw = os.environ.get("TW_COOKIES", "[]")
        try:
            for c in json.loads(tw):
                domain = c.get("domain", ".x.com")
                secure = "TRUE" if c.get("secure") else "FALSE"
                exp = str(int(c.get("expirationDate", 0))) if c.get("expirationDate") else "0"
                f.write(f"{domain}\tTRUE\t{c.get('path','/')}\t{secure}\t{exp}\t{c['name']}\t{c['value']}\n")
        except: pass
    
    return cookie_file

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

def dl(url, quality="480", is_video=True, is_playlist=False):
    if is_playlist:
        opts_pl = {
            'extract_flat': True,
            'playlistend': 50,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': COOKIES_FILE
        }
        try:
            with yt_dlp.YoutubeDL(opts_pl) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info or 'entries' not in info: return None, "قائمة تشغيل فارغة أو غير متاحة"
            return "PLAYLIST_DATA", info['entries']
        except Exception as e:
            return None, str(e)[:200]

    if is_video:
        fmt = f'best[height<={quality}]/best'
    else:
        fmt = 'bestaudio/best'
    
    opts = {
        'outtmpl': '/tmp/dl/%(title).50s.%(ext)s',
        'format': fmt,
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'retries': 5, 'socket_timeout': 60,
        'cookiefile': COOKIES_FILE,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info: return None, "فشل التحميل"
        
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            exts = ['mp4','mkv','webm','m4a','mp3','ogg','wav']
            for ext in exts:
                if os.path.exists(f"{base}.{ext}"): path = f"{base}.{ext}"; break
        if os.path.exists(path): return path, info.get('title', 'بدون عنوان')
        return None, "الملف غير موجود"
    except Exception as e:
        err = str(e)
        if "private" in err.lower(): return None, "المحتوى خاص"
        if "login" in err.lower(): return None, "يتطلب تسجيل دخول - حدث الكوكيز"
        if "not available" in err.lower(): return None, "غير متاح"
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
            
            ac(q["id"], f"تجهيز الطلب...")
            
            if is_pl:
                em(cid, mid, "⏳ جاري فحص قائمة التشغيل وسحب الروابط...")
                status, entries = dl(url, quality, True, is_playlist=True)
                if status == "PLAYLIST_DATA":
                    total = len(entries)
                    em(cid, mid, f"📋 تم الفحص! القائمة تحتوي على {total} فيديو.\n⏳ جاري تحميل وإرسال الفيديوهات بالتتابع...")
                    
                    for index, entry in enumerate(entries, 1):
                        v_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                        em(cid, mid, f"⏳ جاري معالجة الفيديو [{index}/{total}]:\n{entry.get('title', 'بدون عنوان')}")
                        
                        v_path, v_title = dl(v_url, quality, True, is_playlist=False)
                        if v_path and os.path.exists(v_path):
                            v_size = os.path.getsize(v_path)//(1024*1024)
                            if v_size <= 50:
                                try:
                                    with open(v_path, 'rb') as f:
                                        session.post(f"{API}/sendVideo", data={"chat_id": cid, "supports_streaming": True, "caption": f"🎬 [{index}/{total}] {v_title}\n📦 {v_size}MB | {quality}p"}, files={"video": f}, timeout=300)
                                except: pass
                            try: os.remove(v_path)
                            except: pass
                    em(cid, mid, f"✅ اكتمل تحميل وإرسال قائمة التشغيل بالكامل ({total} فيديو) بنجاح!")
                else:
                    em(cid, mid, f"❌ {entries}")
            else:
                em(cid, mid, f"⏳ تحميل فيديو {quality}p...")
                path, title = dl(url, quality, True, is_playlist=False)
                if path and os.path.exists(path):
                    size = os.path.getsize(path)//(1024*1024)
                    if size > 50:
                        em(cid, mid, f"⚠️ كبير ({size}MB)\nجرب جودة أقل")
                    else:
                        try:
                            with open(path,'rb') as f:
                                session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"✅ {title}\n📦 {size}MB | {quality}p"}, files={"video":f}, timeout=300)
                            em(cid, mid, f"✅ {title}\n{quality}p")
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
    print("⚡ البوت v4.0 يعمل...")
    while True:
        try:
            r = session.get(f"{API}/getUpdates", params={"offset":offset+1,"timeout":15}, timeout=20)
            if r.status_code != 200: time.sleep(2); continue
            for u in r.json().get("result", []):
                offset = u["update_id"]
                process(u)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run()
