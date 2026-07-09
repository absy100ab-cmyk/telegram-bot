import requests, time, os, json, hashlib
import yt_dlp

TOKEN = os.environ.get("TOKEN", "8952358620:AAFhrUkYVJvvVAnrWKiCuy7TR122Vt7ilXg")
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
🎵 أو اختر صوت MP3
📋 أرسل رابط قائمة تشغيل

⚡ /start | /help | /about | /settings
👨‍💻 @B43lB"""

ABOUT_MSG = """🤖 **بوت التحميل v4.0**
📥 يوتيوب - تيك توك - انستغرام
🐦 تويتر - فيسبوك - سناب شات
📌 بنترست - 📋 قوائم التشغيل
🎥 144p إلى 1080p
🎵 صوت MP3 128kbps
🔒 آمن - 24 ساعة
👨‍💻 @B43lB"""

SETTINGS_MSG = """⚙️ **الإعدادات v4.0**
🎥 الجودة: 144p - 1080p
🎵 الصوت: MP3 128kbps
📦 الحد: 50MB
📋 قوائم التشغيل: حتى 50 فيديو
🔐 كوكيز يوتيوب ✅ فيسبوك ✅ تويتر ✅"""

def build_cookies():
    cookie_file = "/tmp/dl/cookies.txt"
    
    yt_default = '[{"name":"VISITOR_PRIVACY_METADATA","value":"CgJJURIEGgAgXA%3D%3D","domain":".youtube.com","path":"/","secure":true,"expirationDate":1799114044},{"name":"YSC","value":"U4xbpyeEGmk","domain":".youtube.com","path":"/","secure":true},{"name":"VISITOR_INFO1_LIVE","value":"v6N_ZfSDZ80","domain":".youtube.com","path":"/","secure":true,"expirationDate":1799114044},{"name":"GPS","value":"1","domain":".youtube.com","path":"/","secure":true,"expirationDate":1783563752}]'
    fb_default = '[{"name":"datr","value":"7P9Oahnuht8EWp1SSmbxgje-","domain":".facebook.com","path":"/","secure":true,"expirationDate":1818122220},{"name":"c_user","value":"61551071541200","domain":".facebook.com","path":"/","secure":true,"expirationDate":1815098497},{"name":"xs","value":"40%3AhYeF5Yk9Ffcp8Q%3A2%3A1783562494%3A-1%3A-1","domain":".facebook.com","path":"/","secure":true,"expirationDate":1815098497}]'
    tw_default = '[{"name":"auth_token","value":"76a0fa722ef3e21008fc7da816cd433c098fae94","domain":".x.com","path":"/","secure":true,"expirationDate":1815098930},{"name":"ct0","value":"9382e5d47ada2e59528c9a735858ddc121c72059be19d7a25145f10ed6189f408d445ecdb843aabcf273363d7ebe9db4d0cb7c6194afab63a66de126a8440fd109ece80424e92db9e9aa955cc1076dc3","domain":".x.com","path":"/","secure":true,"expirationDate":1818122931}]'
    
    with open(cookie_file, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        for key, domain, default in [("YT_COOKIES", ".youtube.com", yt_default), ("FB_COOKIES", ".facebook.com", fb_default), ("TW_COOKIES", ".x.com", tw_default)]:
            try:
                for c in json.loads(os.environ.get(key, default)):
                    sec = "TRUE" if c.get("secure") else "FALSE"
                    exp = str(int(c.get("expirationDate", 0))) if c.get("expirationDate") else "0"
                    f.write(f"{c.get('domain', domain)}\tTRUE\t{c.get('path','/')}\t{sec}\t{exp}\t{c['name']}\t{c['value']}\n")
            except: pass
    return cookie_file

COOKIES = build_cookies()

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

def download(url, quality="480", audio_only=False):
    fmt = 'bestaudio/best' if audio_only else f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'
    
    # إعدادات أساسية
    opts = {
        'outtmpl': '/tmp/dl/%(title).50s.%(ext)s',
        'format': fmt,
        'merge_output_format': None if audio_only else 'mp4',
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'retries': 5, 'socket_timeout': 60, 'cookiefile': COOKIES,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'http_headers': {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9'}
    }
    
    # إعدادات خاصة بفيسبوك
    if 'facebook.com' in url.lower() or 'fb.com' in url.lower() or 'fb.watch' in url.lower():
        opts['extractor_args'] = {'facebook': {'format': 'browser'}}
        opts['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        opts['http_headers']['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
    
    # إعدادات خاصة بانستغرام
    if 'instagram.com' in url.lower():
        opts['extractor_args'] = {'instagram': {'api': 'web'}}
    
    # إعدادات خاصة بتويتر
    if 'twitter.com' in url.lower() or 'x.com' in url.lower():
        opts['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
        opts['http_headers']['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
    
    if audio_only:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info: return None, "فشل التحميل"
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            for ext in (['mp3'] if audio_only else ['mp4','mkv','webm']):
                if os.path.exists(f"{base}.{ext}"): path = f"{base}.{ext}"; break
        if os.path.exists(path): return path, info.get('title', 'بدون عنوان')
        return None, "الملف غير موجود"
    except Exception as e:
        err = str(e)
        if "private" in err.lower(): return None, "المحتوى خاص"
        if "login" in err.lower(): return None, "يتطلب تسجيل دخول"
        return None, err[:200]

def get_playlist(url):
    opts = {'extract_flat': True, 'playlistend': 50, 'quiet': True, 'no_warnings': True, 'cookiefile': COOKIES}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info.get('entries', []) if info else []
    except: return []

def process(u):
    if "callback_query" in u:
        q = u["callback_query"]
        cid = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        d = q["data"]
        
        if d.startswith("q_"):
            _, key, quality = d.split("_")
            if key not in urls: ac(q["id"], "انتهت الجلسة", True); return
            url = urls[key]
            is_pl = "playlist" in url.lower() or "list=" in url.lower()
            
            if is_pl:
                ac(q["id"], "فحص القائمة...")
                em(cid, mid, "⏳ فحص قائمة التشغيل...")
                entries = get_playlist(url)
                if not entries:
                    em(cid, mid, "❌ قائمة فارغة أو غير متاحة")
                    return
                
                total = len(entries)
                for i, entry in enumerate(entries, 1):
                    vid = entry.get('id', '')
                    vurl = entry.get('url') or f"https://youtube.com/watch?v={vid}"
                    vtitle = entry.get('title', f'فيديو {i}')
                    
                    em(cid, mid, f"⏳ [{i}/{total}] {vtitle}")
                    path, title = download(vurl, quality)
                    
                    if path and os.path.exists(path):
                        size = os.path.getsize(path)//(1024*1024)
                        if size <= 50:
                            try:
                                with open(path,'rb') as f:
                                    session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"[{i}/{total}] {title}\n{size}MB | {quality}p"}, files={"video":f}, timeout=300)
                            except: pass
                        try: os.remove(path)
                        except: pass
                
                em(cid, mid, f"✅ اكتملت!\n{total} فيديو")
            
            else:
                ac(q["id"], f"تحميل {quality}p...")
                em(cid, mid, f"⏳ تحميل {quality}p...")
                path, title = download(url, quality)
                
                if path and os.path.exists(path):
                    size = os.path.getsize(path)//(1024*1024)
                    if size > 50:
                        em(cid, mid, f"⚠️ كبير ({size}MB)")
                    else:
                        try:
                            with open(path,'rb') as f:
                                session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"✅ {title}\n{size}MB | {quality}p"}, files={"video":f}, timeout=300)
                            em(cid, mid, f"✅ {title}")
                        except: em(cid, mid, "❌ فشل الإرسال")
                    try: os.remove(path)
                    except: pass
                else: em(cid, mid, f"❌ {title}")
        
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls: ac(q["id"], "انتهت الجلسة", True); return
            ac(q["id"], "تحميل صوت...")
            em(cid, mid, "⏳ تحميل الصوت...")
            path, title = download(urls[key], audio_only=True)
            if path and os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        session.post(f"{API}/sendAudio", data={"chat_id":cid,"caption":f"🎵 {title}"}, files={"audio":f}, timeout=300)
                    em(cid, mid, f"✅ {title}")
                except: em(cid, mid, "❌ فشل الإرسال")
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
            is_pl = "playlist" in txt.lower() or "list=" in txt.lower()
            
            kb = json.dumps({"inline_keyboard": [
                [{"text": "🎥 144p", "callback_data": f"q_{key}_144"}, {"text": "🎥 360p", "callback_data": f"q_{key}_360"}],
                [{"text": "🎥 480p", "callback_data": f"q_{key}_480"}, {"text": "🎥 720p", "callback_data": f"q_{key}_720"}],
                [{"text": "🎥 1080p", "callback_data": f"q_{key}_1080"}],
                [{"text": "🎵 صوت MP3", "callback_data": f"a_{key}"}]
            ]})
            
            msg = "✅ **تم استلام الرابط**"
            if is_pl: msg += "\n📋 **قائمة تشغيل**"
            msg += "\n\n**اختر الجودة أو الصوت:**"
            sm(cid, msg, kb)

def run():
    global offset
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
