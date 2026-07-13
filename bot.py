import requests, time, os, json, hashlib, re
import yt_dlp

# ===== التوكن من المتغيرات البيئية =====
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ خطأ: لم يتم تعيين TOKEN في المتغيرات البيئية")
    print("📝 قم بتعيينه باستخدام: export TOKEN='your_bot_token'")
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

HELP_MSG = """🆘 أرسل رابط الفيديو ثم اختر الجودة أو الصوت."""
ABOUT_MSG = """🤖 بوت التحميل v5\n🎥 144p-1080p | 🎵 MP3\n👨‍💻 @B43lB"""
SETTINGS_MSG = """⚙️ الجودة: 144p-1080p | الصوت: MP3"""

# ===== كوكيز تيك توك وبنترست =====
COOKIES_FILE = "/tmp/dl/cookies.txt"
COOKIES_CONTENT = """# Netscape HTTP Cookie File
# TikTok Cookies
.tiktok.com	TRUE	/	TRUE	1735689600	tt_webid	v1_abc123def456
.tiktok.com	TRUE	/	TRUE	1735689600	sessionid	abc123xyz789
.tiktok.com	TRUE	/	TRUE	1735689600	tt_csrf_token	xyz789abc123
.tiktok.com	TRUE	/	TRUE	1735689600	tt_chain_token	chain123token
.tiktok.com	TRUE	/	TRUE	1735689600	msToken	ms_token_xyz789

# Pinterest Cookies
.pinterest.com	TRUE	/	TRUE	1735689600	csrftoken	csrf_token_abc123
.pinterest.com	TRUE	/	TRUE	1735689600	sessionid	session_xyz789
.pinterest.com	TRUE	/	TRUE	1735689600	_ir	ir_token_123
.pinterest.com	TRUE	/	TRUE	1735689600	_pinterest_sess	sess_data_abc
.pinterest.com	TRUE	/	TRUE	1735689600	_ga	GA1.2.123456789

# YouTube Cookies
.youtube.com	TRUE	/	TRUE	0	CONSENT	YES+cb
.youtube.com	TRUE	/	TRUE	1735689600	VISITOR_INFO1_LIVE	visitor_token_abc
.youtube.com	TRUE	/	TRUE	1735689600	PREF	pref_token_xyz
"""

with open(COOKIES_FILE, 'w') as f:
    f.write(COOKIES_CONTENT)

print(f"✅ تم حفظ الكوكيز في {COOKIES_FILE}")

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

def download(url, quality="720", audio=False):
    # معالجة بنترست
    if 'pinterest.com' in url.lower() or 'pin.it' in url.lower():
        try:
            h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            r = session.get(url, headers=h, timeout=15)
            html = r.text
            
            # البحث عن فيديو
            v = re.findall(r'"(https?://[^"]*\.mp4[^"]*)"', html)
            if v:
                vurl = v[0].replace('\\', '')
                path = f"/tmp/dl/p_{int(time.time())}.mp4"
                r2 = session.get(vurl, headers=h, timeout=120)
                with open(path, 'wb') as f: f.write(r2.content)
                if os.path.exists(path) and os.path.getsize(path) > 10000:
                    return path, "Pinterest"
            
            # البحث عن صورة
            i = re.findall(r'"(https?://i\.pinimg\.com/originals/[^"]*\.(jpg|png)[^"]*)"', html)
            if i:
                iurl = i[0][0].replace('\\', '')
                path = f"/tmp/dl/p_{int(time.time())}.{i[0][1]}"
                r2 = session.get(iurl, headers=h, timeout=60)
                with open(path, 'wb') as f: f.write(r2.content)
                if os.path.exists(path): return path, "Pinterest"
            return None, "لم يتم العثور على محتوى"
        except Exception as e:
            return None, str(e)[:200]

    # إعدادات yt-dlp
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
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        ]),
        'extractor_args': {
            'tiktok': {
                'app_version': ['34.1.2'],
                'device_type': ['iPhone13,3'],
                'os_version': ['16.0'],
                'os': ['ios'],
            },
            'youtube': {
                'skip': ['hls', 'dash'],
                'player_client': ['android'],
            }
        }
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
                if os.path.exists(f"{base}.{e}"): path = f"{base}.{e}"; break
        if os.path.exists(path): return path, info.get('title','')
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
            if key not in urls: ac(q["id"], "انتهت"); return
            ac(q["id"], "تحميل...")
            em(cid, mid, f"⏳ تحميل {quality}p...")
            path, title = download(urls[key], quality)
            if path and os.path.exists(path):
                size = os.path.getsize(path)//(1024*1024)
                if size > 50:
                    em(cid, mid, f"⚠️ كبير ({size}MB)")
                else:
                    try:
                        with open(path,'rb') as f:
                            if path.endswith(('.jpg','.png')):
                                session.post(f"{API}/sendPhoto", data={"chat_id":cid,"caption":f"✅ {title}"}, files={"photo":f}, timeout=300)
                            else:
                                session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"✅ {title}\n{size}MB | {quality}p"}, files={"video":f}, timeout=300)
                        em(cid, mid, f"✅ {title}")
                    except Exception as e:
                        em(cid, mid, f"❌ فشل الإرسال: {str(e)[:100]}")
                try: os.remove(path)
                except: pass
            else: em(cid, mid, f"❌ {title}")
        
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls: ac(q["id"], "انتهت"); return
            ac(q["id"], "تحميل صوت...")
            em(cid, mid, "⏳ تحميل الصوت...")
            path, title = download(urls[key], audio=True)
            if path and os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        session.post(f"{API}/sendAudio", data={"chat_id":cid,"caption":f"🎵 {title}"}, files={"audio":f}, timeout=300)
                    em(cid, mid, f"✅ {title}")
                except: em(cid, mid, "فشل")
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
            kb = json.dumps({"inline_keyboard": [
                [{"text": "🎥 144p", "callback_data": f"q_{key}_144"}, {"text": "🎥 360p", "callback_data": f"q_{key}_360"}],
                [{"text": "🎥 480p", "callback_data": f"q_{key}_480"}, {"text": "🎥 720p", "callback_data": f"q_{key}_720"}],
                [{"text": "🎥 1080p", "callback_data": f"q_{key}_1080"}],
                [{"text": "🎵 صوت MP3", "callback_data": f"a_{key}"}]
            ]})
            sm(cid, "✅ تم استلام الرابط\nاختر:", kb)

def run():
    global offset
    print("⚡ البوت يعمل مع كوكيز تيك توك وبنترست...")
    print(f"🤖 التوكن: {TOKEN[:10]}...")
    while True:
        try:
            r = session.get(f"{API}/getUpdates", params={"offset":offset+1,"timeout":15}, timeout=20)
            if r.status_code != 200: time.sleep(2); continue
            for u in r.json().get("result", []):
                offset = u["update_id"]
                process(u)
        except: time.sleep(3)

if __name__ == "__main__":
    import random
    run()
