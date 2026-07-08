import requests
import time
import os
import json
import hashlib
import yt_dlp

# قراءة التوكن بأمان من متغيرات Railway بدون كشفه
TOKEN = os.environ.get("TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
os.makedirs(os.path.expanduser("~/dl"), exist_ok=True)
session = requests.Session()
session.headers.update({"Connection": "keep-alive", "User-Agent": "Mozilla/5.0"})

START_MSG = """👋 أهلاً بك!
📩 أرسل رابط الوسيط الذي ترغب بإدارته أو مشاركته.

📌 يرجى التأكد من أن لديك الحق الكامل لاستخدام الرابط المُرسل.

✅ جاهز؟ فقط أرسل الرابط لبدء المعالجة.

المالك ✓ @B43lB"""

HELP_MSG = """🆘 **المساعدة**
📥 أرسل رابط الفيديو
🎥 اختر الجودة | 🎵 اختر صوت
📱 +12 منصة مدعومة

⚡ /start | /help | /about | /settings
👨‍💻 @B43lB"""

ABOUT_MSG = """🤖 **بوت التحميل v3.1**
📥 يوتيوب - تيك توك - انستغرام
🐦 تويتر - فيسبوك - سناب شات
🎥 فيديو (144p - 1080p)
🎵 صوت MP3 128kbps
⚡ سريع - مجاني - 24 ساعة
👨‍💻 @B43lB"""

SETTINGS_MSG = """⚙️ **الإعدادات الحالية**
🎥 الجودة: اختيارية (144p - 1080p)
🎵 الصوت: 128kbps MP3
📦 الحد: 50MB
🔐 جميع المنصات مدعومة"""

COOKIES_FILE = os.path.expanduser("~/dl/cookies.txt")
os.makedirs(os.path.dirname(COOKIES_FILE), exist_ok=True)
with open(COOKIES_FILE, 'w') as f:
    f.write("# Netscape HTTP Cookie File\n")
    # يوتيوب
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tCONSENT\tYES+cb.20250201-00-p0.en+FX+999\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tSOCS\tCAESNQgDEitib3F1X2lkbGVudGl0eWZyb250ZW5kdWlfc2VydmVyXzIwMjUwMjA0LjAxX3A\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tVISITOR_INFO1_LIVE\t_TJdGkqQv5w\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tYSC\t_mv2Q0sJkY4\n")
    # انستغرام
    f.write(".instagram.com\tTRUE\t/\tTRUE\t1818046805\tdatr\tVtlNahdqMNc3JGGX7oF47l9T\n")
    f.write(".instagram.com\tTRUE\t/\tFALSE\t1791263392\tds_user_id\t2231760860\n")
    f.write(".instagram.com\tTRUE\t/\tFALSE\t1818047392\tcsrftoken\t5L5Q1H7peABxuyAYAO930xsaKhqHQ11S\n")
    f.write(".instagram.com\tTRUE\t/\tTRUE\t1815022805\tig_did\tA993E926-2AEC-482E-B79B-2C48328BD145\n")
    f.write(".instagram.com\tTRUE\t/\tFALSE\t1818046808\tmid\tak3ZVgABAAE0e5WLt-6gysGmteVh\n")
    f.write(".instagram.com\tTRUE\t/\tTRUE\t1815023383\tsessionid\t2231760860%3ANw832ysVMQDbd0%3A24%3AAYiuSrd7XDdPb5_I5JeX0wr3S4eS3_tXvtDO2ovSxw\n")
    # تويتر
    f.write(".twitter.com\tTRUE\t/\tTRUE\t0\tauth_token\t0000000000000000000000000000000000000000\n")
    f.write(".twitter.com\tTRUE\t/\tTRUE\t0\tct0\t0000000000000000000000000000000000000000\n")
    f.write(".x.com\tTRUE\t/\tTRUE\t0\tauth_token\t0000000000000000000000000000000000000000\n")
    # فيسبوك
    f.write(".facebook.com\tTRUE\t/\tTRUE\t0\tc_user\t100000000000000\n")
    f.write(".facebook.com\tTRUE\t/\tTRUE\t0\txs\t0000000000000000000000000000000000000000\n")

def sm(cid, txt, kb=None):
    try:
        p = {"chat_id": cid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/sendMessage", json=p, timeout=5)
    except: pass

def em(cid, mid, txt, kb=None):
    try:
        p = {"chat_id": cid, "message_id": mid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/editMessageText", json=p, timeout=5)
    except: pass

def ac(qid, txt, alert=False):
    try: session.post(f"{API}/answerCallbackQuery", json={"callback_query_id": qid, "text": txt, "show_alert": alert}, timeout=2)
    except: pass

def dl(url, quality="480", is_video=True):
    if is_video:
        fmt = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'
    else:
        fmt = 'bestaudio/best'
    
    opts = {
        'outtmpl': os.path.expanduser('~/dl/%(title).50s.%(ext)s'),
        'format': fmt,
        'merge_output_format': 'mp4' if is_video else None,
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'retries': 5, 'socket_timeout': 45,
        'cookiefile': COOKIES_FILE,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    if not is_video:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info: return None, "فشل التحميل"
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            exts = ['mp4','mkv','webm'] if is_video else ['mp3']
            for ext in exts:
                if os.path.exists(f"{base}.{ext}"): path = f"{base}.{ext}"; break
        if os.path.exists(path): return path, info.get('title', 'بدون عنوان')
        return None, "الملف غير موجود"
    except Exception as e:
        err = str(e)
        if "private" in err.lower(): return None, "المحتوى خاص"
        if "login" in err.lower(): return None, "يتطلب تسجيل دخول"
        if "not available" in err.lower(): return None, "غير متاح"
        return None, err[:200]

def save_urls():
    try:
        with open(os.path.expanduser('~/dl/urls.json'), 'w') as f: json.dump(urls, f)
    except: pass

def load_urls():
    global urls
    try:
        with open(os.path.expanduser('~/dl/urls.json'), 'r') as f: urls = json.load(f)
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
            if key not in urls: ac(q["id"], "انتهت الجلسة", True); return
            ac(q["id"], f"تحميل {quality}p...")
            em(cid, mid, f"⏳ تحميل فيديو {quality}p...")
            path, title = dl(urls[key], quality, True)
            if path and os.path.exists(path):
                size = os.path.getsize(path)//(1024*1024)
                if size > 50:
                    em(cid, mid, f"⚠️ كبير ({size}MB)\nجرب جودة أقل أو صوت")
                else:
                    try:
                        with open(path,'rb') as f:
                            session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"✅ {title}\n📦 {size}MB | {quality}p"}, files={"video":f}, timeout=180)
                        em(cid, mid, f"✅ {title}\n{quality}p")
                    except: em(cid, mid, "فشل الإرسال")
                try: os.remove(path)
                except: pass
            else: em(cid, mid, f"❌ {title}")
        
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls: ac(q["id"], "انتهت الجلسة", True); return
            ac(q["id"], "تحميل صوت...")
            em(cid, mid, "⏳ تحميل الصوت...")
            path, title = dl(urls[key], "480", False)
            if path and os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        session.post(f"{API}/sendAudio", data={"chat_id":cid,"caption":f"🎵 {title}"}, files={"audio":f}, timeout=180)
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
            kb = json.dumps({"inline_keyboard": [
                [{"text": "🎥 144p", "callback_data": f"q_{key}_144"}, {"text": "🎥 360p", "callback_data": f"q_{key}_360"}],
                [{"text": "🎥 480p", "callback_data": f"q_{key}_480"}, {"text": "🎥 720p", "callback_data": f"q_{key}_720"}],
                [{"text": "🎥 1080p", "callback_data": f"q_{key}_1080"}],
                [{"text": "🎵 صوت MP3", "callback_data": f"a_{key}"}]
            ]})
            sm(cid, "✅ **تم استلام الرابط**\n\n**اختر الجودة أو الصوت:**", kb)

def run():
    global offset
    load_urls()
    print("⚡ البوت يعمل على Railway...")
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
