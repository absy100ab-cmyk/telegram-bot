import requests, time, os, json, hashlib, re
import yt_dlp
import random
import subprocess

# ===== التحقق من FFmpeg =====
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg مثبت")
        return True
    except:
        print("❌ FFmpeg غير مثبت!")
        print("📝 قم بتشغيل: sudo apt install ffmpeg -y")
        return False

check_ffmpeg()

# ===== التوكن من المتغيرات البيئية =====
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ خطأ: لم يتم تعيين TOKEN")
    print("📝 استخدم: export TOKEN='your_bot_token'")
    exit(1)

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

# ===== كوكيز =====
COOKIES_FILE = "/tmp/dl/cookies.txt"
COOKIES_CONTENT = """# Netscape HTTP Cookie File
.tiktok.com	TRUE	/	TRUE	1735689600	tt_webid	v1_abc123def456
.tiktok.com	TRUE	/	TRUE	1735689600	sessionid	abc123xyz789
.pinterest.com	TRUE	/	TRUE	1735689600	csrftoken	csrf_token_abc123
.pinterest.com	TRUE	/	TRUE	1735689600	sessionid	session_xyz789
.youtube.com	TRUE	/	TRUE	0	CONSENT	YES+cb
"""

with open(COOKIES_FILE, 'w') as f:
    f.write(COOKIES_CONTENT)

print(f"✅ تم حفظ الكوكيز")

def sm(cid, txt, kb=None):
    try:
        p = {"chat_id": cid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/sendMessage", json=p, timeout=10)
    except Exception as e:
        print(f"❌ خطأ في الإرسال: {e}")

def em(cid, mid, txt, kb=None):
    try:
        p = {"chat_id": cid, "message_id": mid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/editMessageText", json=p, timeout=10)
    except: pass

def ac(qid, txt, alert=False):
    try: 
        session.post(f"{API}/answerCallbackQuery", json={"callback_query_id": qid, "text": txt, "show_alert": alert}, timeout=5)
    except: pass

def download(url, quality="720", audio=False):
    # معالجة بنترست
    if 'pinterest.com' in url.lower() or 'pin.it' in url.lower():
        try:
            h = {'User-Agent': 'Mozilla/5.0'}
            r = session.get(url, headers=h, timeout=15)
            html = r.text
            v = re.findall(r'"(https?://[^"]*\.mp4[^"]*)"', html)
            if v:
                path = f"/tmp/dl/p_{int(time.time())}.mp4"
                r2 = session.get(v[0].replace('\\', ''), headers=h, timeout=120)
                with open(path, 'wb') as f: f.write(r2.content)
                if os.path.exists(path): return path, "Pinterest"
            return None, "لا يوجد فيديو"
        except Exception as e:
            return None, str(e)[:200]

    fmt = 'bestaudio/best' if audio else f'best[height<={quality}]/best'
    opts = {
        'outtmpl': '/tmp/dl/%(title).60s.%(ext)s',
        'format': fmt,
        'merge_output_format': None if audio else 'mp4',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'retries': 10,
        'fragment_retries': 10,
        'socket_timeout': 60,
        'cookiefile': COOKIES_FILE,
        'user_agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        ]),
    }
    
    if audio:
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info: return None, "فشل"
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            for e in (['mp3'] if audio else ['mp4','mkv','webm']):
                if os.path.exists(f"{base}.{e}"): 
                    path = f"{base}.{e}"
                    break
        if os.path.exists(path): 
            return path, info.get('title', 'فيديو')
        return None, "ملف غير موجود"
    except Exception as e:
        return None, str(e)[:200]

def process(u):
    if "callback_query" in u:
        q = u["callback_query"]
        cid = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        d = q["data"]
        
        if d.startswith("q_"):
            _, key, quality = d.split("_")
            if key not in urls: 
                ac(q["id"], "انتهت", True)
                return
            ac(q["id"], "⏳ جاري التحميل...")
            em(cid, mid, f"⏳ تحميل {quality}p...")
            path, title = download(urls[key], quality)
            if path and os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        if path.endswith(('.jpg','.png')):
                            session.post(f"{API}/sendPhoto", data={"chat_id":cid,"caption":f"✅ {title}"}, files={"photo":f}, timeout=300)
                        else:
                            session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"✅ {title}"}, files={"video":f}, timeout=300)
                    em(cid, mid, f"✅ تم التحميل!")
                except Exception as e:
                    em(cid, mid, f"❌ {str(e)[:100]}")
                try: os.remove(path)
                except: pass
            else: 
                em(cid, mid, f"❌ {title}")
        
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls:
                ac(q["id"], "انتهت", True)
                return
            ac(q["id"], "⏳ جاري تحميل الصوت...")
            em(cid, mid, "⏳ تحميل الصوت...")
            path, title = download(urls[key], audio=True)
            if path and os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        session.post(f"{API}/sendAudio", data={"chat_id":cid,"caption":f"🎵 {title}"}, files={"audio":f}, timeout=300)
                    em(cid, mid, f"✅ تم التحميل!")
                except Exception as e:
                    em(cid, mid, f"❌ {str(e)[:100]}")
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
        elif txt.startswith("http"):
            key = hashlib.md5(txt.encode()).hexdigest()[:8]
            urls[key] = txt
            kb = json.dumps({"inline_keyboard": [
                [{"text": "🎥 144p", "callback_data": f"q_{key}_144"}, {"text": "🎥 360p", "callback_data": f"q_{key}_360"}],
                [{"text": "🎥 480p", "callback_data": f"q_{key}_480"}, {"text": "🎥 720p", "callback_data": f"q_{key}_720"}],
                [{"text": "🎥 1080p", "callback_data": f"q_{key}_1080"}],
                [{"text": "🎵 صوت MP3", "callback_data": f"a_{key}"}]
            ]})
            sm(cid, "✅ تم استلام الرابط\nاختر:", kb)

def run():
    global offset
    print("="*50)
    print("⚡ تشغيل البوت...")
    print(f"🤖 TOKEN: {TOKEN[:10]}...")
    print("="*50)
    
    while True:
        try:
            r = session.get(f"{API}/getUpdates", params={"offset":offset+1,"timeout":30}, timeout=35)
            if r.status_code != 200:
                print(f"⚠️ خطأ في الاتصال: {r.status_code}")
                time.sleep(5)
                continue
                
            data = r.json()
            if not data.get("ok"):
                print(f"❌ خطأ من Telegram: {data}")
                time.sleep(5)
                continue
                
            for u in data.get("result", []):
                offset = u["update_id"]
                process(u)
                
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run()
