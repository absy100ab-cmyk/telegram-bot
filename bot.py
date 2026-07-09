import requests, time, os, json, hashlib, re
import yt_dlp

TOKEN = os.environ.get("TOKEN", "8952358620:AAFhrUkYVJvvVAnrWKiCuy7TR122Vt7ilXg")
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
os.makedirs("/tmp/dl", exist_ok=True)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"})

START_MSG = """👋 أهلاً بك!
📩 أرسل رابط الفيديو للتحميل.
🎥 اختر الجودة أو 🎵 صوت MP3.
📱 يوتيوب | تيك توك | انستغرام | تويتر | فيسبوك | بنترست
المالك ✓ @B43lB"""

HELP_MSG = """🆘 أرسل رابط الفيديو ثم اختر الجودة أو الصوت."""

ABOUT_MSG = """🤖 بوت التحميل - الإصدار النهائي
🎥 144p - 1080p | 🎵 MP3 | 📌 بنترست
👨‍💻 @B43lB"""

SETTINGS_MSG = """⚙️ الجودة: 144p-1080p | الصوت: MP3"""

COOKIES_FILE = "/tmp/dl/cookies.txt"
with open(COOKIES_FILE, 'w') as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tCONSENT\tYES+cb\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tGPS\t1\n")

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

def is_image(path):
    return path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))

def is_video(path):
    return path.lower().endswith(('.mp4', '.mkv', '.webm', '.mov'))

def download_media(url, quality="720", audio_only=False):
    # === Pinterest ===
    if 'pinterest.com' in url.lower() or 'pin.it' in url.lower():
        try:
            h = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'}
            r = session.get(url, headers=h, timeout=15)
            html = r.text
            
            # فيديو
            vids = re.findall(r'"(https?://[^"]*?\.mp4[^"]*)"', html)
            if vids:
                vurl = vids[0].replace('\\', '').split('?')[0]
                path = f"/tmp/dl/pinvid_{int(time.time())}.mp4"
                r2 = session.get(vurl, headers=h, timeout=120)
                with open(path, 'wb') as f: f.write(r2.content)
                if os.path.exists(path) and os.path.getsize(path) > 50000:
                    return path, "فيديو Pinterest"
            
            # صورة أصلية
            imgs = re.findall(r'"(https?://i\.pinimg\.com/originals/[^"]*\.(jpg|png|jpeg)[^"]*)"', html)
            if imgs:
                iurl = imgs[0][0].replace('\\', '').split('?')[0]
                ext = imgs[0][1]
                path = f"/tmp/dl/pinimg_{int(time.time())}.{ext}"
                r2 = session.get(iurl, headers=h, timeout=60)
                with open(path, 'wb') as f: f.write(r2.content)
                if os.path.exists(path): return path, "صورة Pinterest"
            
            return None, "لم يتم العثور على محتوى"
        except Exception as e:
            return None, str(e)[:200]
    
    # === باقي المنصات ===
    if audio_only:
        fmt = 'bestaudio/best'
        merge = None
    else:
        fmt = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best[height<={quality}]/best'
        merge = 'mp4'
    
    opts = {
        'outtmpl': '/tmp/dl/%(title).60s.%(ext)s',
        'format': fmt,
        'merge_output_format': merge,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'retries': 10,
        'fragment_retries': 10,
        'socket_timeout': 90,
        'cookiefile': COOKIES_FILE,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8'
        }
    }
    
    if audio_only:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        if not info: return None, "فشل التحميل"
        
        title = info.get('title', 'بدون عنوان')
        path = ydl.prepare_filename(info)
        
        # العثور على الملف
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            if audio_only:
                if os.path.exists(base + '.mp3'): path = base + '.mp3'
                elif os.path.exists(base + '.m4a'): path = base + '.m4a'
            else:
                for ext in ['.mp4', '.mkv', '.webm', '.mov']:
                    if os.path.exists(base + ext): path = base + ext; break
        
        if not os.path.exists(path):
            dl_dir = '/tmp/dl'
            files = [f for f in os.listdir(dl_dir) if f.endswith(('.mp4','.mkv','.webm','.mov','.mp3','.m4a'))]
            if files:
                latest = max(files, key=lambda x: os.path.getmtime(f"{dl_dir}/{x}"))
                path = f"{dl_dir}/{latest}"
        
        if os.path.exists(path):
            return path, title
        return None, "الملف غير موجود"
        
    except Exception as e:
        err = str(e)
        if "format" in err.lower() and "not available" in err.lower():
            return None, "الجودة غير متاحة - اختر جودة أقل"
        if "login" in err.lower():
            return None, "يتطلب تسجيل دخول"
        if "private" in err.lower():
            return None, "المحتوى خاص"
        if "not found" in err.lower() or "404" in err:
            return None, "الرابط غير موجود"
        return None, err[:300]

def process(u):
    if "callback_query" in u:
        q = u["callback_query"]
        cid = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        d = q["data"]
        
        if d.startswith("q_"):
            _, key, quality = d.split("_")
            if key not in urls:
                ac(q["id"], "انتهت الجلسة - أرسل الرابط مجدداً")
                return
            
            ac(q["id"], f"⏳ تحميل {quality}p...")
            em(cid, mid, f"⏳ جاري تحميل الفيديو بدقة {quality}p...")
            
            path, title = download_media(urls[key], quality)
            
            if path and os.path.exists(path):
                size_mb = os.path.getsize(path) // (1024 * 1024)
                
                if is_image(path):
                    # إرسال كصورة
                    try:
                        with open(path, 'rb') as f:
                            session.post(f"{API}/sendPhoto", data={"chat_id": cid, "caption": f"✅ {title}"}, files={"photo": f}, timeout=300)
                        em(cid, mid, f"✅ {title}\n📷 صورة")
                    except:
                        em(cid, mid, "❌ فشل إرسال الصورة")
                
                elif is_video(path):
                    if size_mb > 50:
                        em(cid, mid, f"⚠️ حجم الفيديو {size_mb}MB\nالحد الأقصى 50MB\nجرب جودة أقل أو صوت")
                    else:
                        try:
                            with open(path, 'rb') as f:
                                session.post(f"{API}/sendVideo", data={
                                    "chat_id": cid,
                                    "supports_streaming": True,
                                    "caption": f"✅ {title}\n📦 {size_mb}MB | 🎥 {quality}p",
                                    "width": 1920,
                                    "height": 1080
                                }, files={"video": f}, timeout=300)
                            em(cid, mid, f"✅ {title}\n📦 {size_mb}MB | {quality}p")
                        except:
                            em(cid, mid, "❌ فشل إرسال الفيديو")
                
                else:
                    # ملف آخر
                    try:
                        with open(path, 'rb') as f:
                            session.post(f"{API}/sendDocument", data={"chat_id": cid, "caption": f"✅ {title}"}, files={"document": f}, timeout=300)
                        em(cid, mid, f"✅ {title}")
                    except:
                        em(cid, mid, "❌ فشل الإرسال")
                
                try: os.remove(path)
                except: pass
            else:
                em(cid, mid, f"❌ {title}")
        
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls:
                ac(q["id"], "انتهت الجلسة")
                return
            
            ac(q["id"], "⏳ تحميل الصوت...")
            em(cid, mid, "⏳ جاري تحميل الصوت...")
            
            path, title = download_media(urls[key], audio_only=True)
            
            if path and os.path.exists(path):
                size_mb = os.path.getsize(path) // (1024 * 1024)
                try:
                    with open(path, 'rb') as f:
                        session.post(f"{API}/sendAudio", data={
                            "chat_id": cid,
                            "caption": f"🎵 {title}\n📦 {size_mb}MB | MP3 192kbps",
                            "title": title
                        }, files={"audio": f}, timeout=300)
                    em(cid, mid, f"✅ {title}\n🎵 MP3 | {size_mb}MB")
                except:
                    em(cid, mid, "❌ فشل إرسال الصوت")
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
    print("⚡ البوت يعمل...")
    while True:
        try:
            r = session.get(f"{API}/getUpdates", params={"offset": offset + 1, "timeout": 15}, timeout=20)
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
