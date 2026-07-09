import requests, time, os, json, hashlib
import yt_dlp

TOKEN = os.environ.get("TOKEN", "8952358620:AAFhrUkYVJvvVAnrWKiCuy7TR122Vt7ilXg")
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
os.makedirs("/tmp/dl", exist_ok=True)
session = requests.Session()

START_MSG = """👋 أهلاً بك!
📩 أرسل رابط الفيديو للتحميل.
🎥 اختر الجودة أو 🎵 صوت MP3.
📱 يوتيوب | تيك توك | انستغرام | تويتر | فيسبوك | بنترست
المالك ✓ @B43lB"""

HELP_MSG = """🆘 أرسل رابط الفيديو ثم اختر الجودة أو الصوت.
⚡ /start | /help | /about | /settings"""

ABOUT_MSG = """🤖 بوت التحميل v5.0
🎥 144p - 1080p | 🎵 MP3
👨‍💻 @B43lB"""

SETTINGS_MSG = """⚙️ الجودة: 144p-1080p | الصوت: MP3"""

COOKIES_FILE = "/tmp/dl/cookies.txt"
with open(COOKIES_FILE, 'w') as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tCONSENT\tYES+cb\n")

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

def download(url, quality="480", audio=False):
    # تحديد الصيغة المناسبة
    if audio:
        fmt = 'bestaudio/best'
    elif 'pinterest.com' in url.lower() or 'pin.it' in url.lower():
        fmt = 'bestvideo+bestaudio/best'
    elif 'instagram.com' in url.lower():
        fmt = 'best'
    else:
        fmt = f'best[height<={quality}]/best'
    
    opts = {
        'outtmpl': '/tmp/dl/%(title).50s.%(ext)s',
        'format': fmt,
        'merge_output_format': None if audio else 'mp4',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'retries': 5,
        'socket_timeout': 60,
        'cookiefile': COOKIES_FILE,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
    }
    
    if audio:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        if not info: return None, "فشل التحميل"
        
        # البحث عن الملف المحمل
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            for ext in (['mp3'] if audio else ['mp4','mkv','webm','mov']):
                if os.path.exists(f"{base}.{ext}"):
                    path = f"{base}.{ext}"
                    break
        
        # إذا ما لقينا، نبحث عن أحدث ملف
        if not os.path.exists(path):
            files = sorted(
                [f"/tmp/dl/{f}" for f in os.listdir('/tmp/dl') if f.endswith(('.mp4','.mkv','.webm','.mp3'))],
                key=os.path.getmtime, reverse=True
            )
            if files: path = files[0]
        
        if os.path.exists(path):
            return path, info.get('title', 'بدون عنوان')
        return None, "الملف غير موجود"
        
    except Exception as e:
        err = str(e)
        if "format" in err.lower():
            return None, "الصيغة غير متاحة - جرب جودة أقل"
        return None, err[:200]

def process(u):
    if "callback_query" in u:
        q = u["callback_query"]
        cid = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        d = q["data"]
        
        if d.startswith("q_"):
            _, key, quality = d.split("_")
            if key not in urls: ac(q["id"], "انتهت الجلسة"); return
            
            ac(q["id"], f"تحميل {quality}p...")
            em(cid, mid, f"⏳ تحميل {quality}p...")
            
            path, title = download(urls[key], quality)
            
            if path and os.path.exists(path):
                size = os.path.getsize(path) // (1024*1024)
                if size > 50:
                    em(cid, mid, f"⚠️ كبير ({size}MB)\nجرب جودة أقل")
                else:
                    try:
                        with open(path, 'rb') as f:
                            session.post(
                                f"{API}/sendVideo",
                                data={"chat_id": cid, "supports_streaming": True, "caption": f"✅ {title}\n📦 {size}MB | {quality}p"},
                                files={"video": f},
                                timeout=300
                            )
                        em(cid, mid, f"✅ {title}")
                    except: em(cid, mid, "❌ فشل الإرسال")
                try: os.remove(path)
                except: pass
            else:
                em(cid, mid, f"❌ {title}")
        
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls: ac(q["id"], "انتهت الجلسة"); return
            
            ac(q["id"], "تحميل صوت...")
            em(cid, mid, "⏳ تحميل الصوت...")
            
            path, title = download(urls[key], audio=True)
            
            if path and os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        session.post(
                            f"{API}/sendAudio",
                            data={"chat_id": cid, "caption": f"🎵 {title}"},
                            files={"audio": f},
                            timeout=300
                        )
                    em(cid, mid, f"✅ {title}")
                except: em(cid, mid, "❌ فشل الإرسال")
                try: os.remove(path)
                except: pass
            else:
                em(cid, mid, f"❌ {title}")
    
    if "message" in u and "text" in u["message"]:
        m = u["message"]
        cid = m["chat"]["id"]
        txt = m["text"].strip()
        
        if txt == "/start":
            sm(cid, START_MSG)
        elif txt == "/help":
            sm(cid, HELP_MSG)
        elif txt == "/about":
            sm(cid, ABOUT_MSG)
        elif txt == "/settings":
            sm(cid, SETTINGS_MSG)
        elif txt.startswith("http"):
            key = hashlib.md5(txt.encode()).hexdigest()[:8]
            urls[key] = txt
            
            kb = json.dumps({"inline_keyboard": [
                [{"text": "🎥 144p", "callback_data": f"q_{key}_144"}, {"text": "🎥 360p", "callback_data": f"q_{key}_360"}],
                [{"text": "🎥 480p", "callback_data": f"q_{key}_480"}, {"text": "🎥 720p", "callback_data": f"q_{key}_720"}],
                [{"text": "🎥 1080p", "callback_data": f"q_{key}_1080"}],
                [{"text": "🎵 صوت MP3", "callback_data": f"a_{key}"}]
            ]})
            
            sm(cid, "✅ تم استلام الرابط\n\nاختر الجودة أو الصوت:", kb)

def run():
    global offset
    print("⚡ البوت v5.0 يعمل...")
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
