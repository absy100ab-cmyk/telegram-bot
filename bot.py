import requests, time, os, json, hashlib
import yt_dlp

TOKEN = "8952358620:AAEicwASxkHEYY20ylqn46YCOJ-Lvxu5wPM"
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
os.makedirs("dl", exist_ok=True)
session = requests.Session()
session.headers.update({"Connection": "keep-alive"})

START_MSG = """👋 أهلاً بك!
📩 أرسل رابط الوسيط الذي ترغب بإدارته أو مشاركته.

📌 يرجى التأكد من أن لديك الحق الكامل لاستخدام الرابط المُرسل.

✅ جاهز؟ فقط أرسل الرابط لبدء المعالجة.

المالك ✓ @B43lB"""

HELP_MSG = """🆘 **المساعدة**

📥 **طريقة الاستخدام:**
1️⃣ أرسل رابط الفيديو
2️⃣ اختر: 🎥 فيديو أو 🎵 صوت MP3
3️⃣ استلم الملف

📱 **المنصات المدعومة:**
• يوتيوب • تيك توك • انستغرام
• تويتر • فيسبوك • سناب شات
• ريديت • تويتش • فيميو
• لينكد إن • بينتريست

⚡ **أوامر البوت:**
/start - تشغيل البوت
/help - المساعدة
/about - عن البوت
/settings - الإعدادات

👨‍💻 المالك: @B43lB"""

ABOUT_MSG = """🤖 **عن البوت**

📥 بوت تحميل الوسائط من مواقع التواصل

📌 **المميزات:**
• تحميل فيديو بجودة عالية
• تحميل صوت MP3
• ضغط تلقائي للفيديوهات الكبيرة
• دعم +12 منصة

🛠 **الإصدار:** 3.0
📅 **آخر تحديث:** 2025

👨‍💻 **المطور:** @B43lB"""

SETTINGS_MSG = """⚙️ **الإعدادات**

🎥 **جودة الفيديو:** متوسطة (سريعة)
🎵 **جودة الصوت:** 128kbps MP3
🗜️ **الضغط:** تلقائي
📦 **الحجم الأقصى:** 50MB

📌 **ملاحظة:** البوت في وضع السرعة"""
SETTINGS_MSG = """⚙️ **الإعدادات**

🎥 **جودة الفيديو:** متوسطة (سريعة)
🎵 **جودة الصوت:** 128kbps MP3
🗜️ **الضغط:** تلقائي
📦 **الحجم الأقصى:** 50MB

📌 **ملاحظة:** البوت في وضع السرعة"""

COOKIES_FILE = "dl/cookies_netscape.txt"
if not os.path.exists(COOKIES_FILE):
    with open(COOKIES_FILE, 'w') as f:
        f.write("""# Netscape HTTP Cookie File
.instagram.com	TRUE	/	TRUE	1818046805	datr	VtlNahdqMNc3JGGX7oF47l9T
.instagram.com	TRUE	/	FALSE	1791263392	ds_user_id	2231760860
.instagram.com	TRUE	/	FALSE	1818047392	csrftoken	5L5Q1H7peABxuyAYAO930xsaKhqHQ11S
.instagram.com	TRUE	/	TRUE	1815022805	ig_did	A993E926-2AEC-482E-B79B-2C48328BD145
.instagram.com	TRUE	/	FALSE	1784092187	wd	360x615
.instagram.com	TRUE	/	FALSE	1818046808	mid	ak3ZVgABAAE0e5WLt-6gysGmteVh
.instagram.com	TRUE	/	TRUE	1815023383	sessionid	2231760860%3ANw832ysVMQDbd0%3A24%3AAYiuSrd7XDdPb5_I5JeX0wr3S4eS3_tXvtDO2ovSxw
.instagram.com	TRUE	/	FALSE	1784091608	dpr	2
.instagram.com	TRUE	/	TRUE	1783574009	rur	RVA%2C17841402185808970%2C1784697209%3A01ff1206401fda5ed379a32820f16576b801dcda36b681ce53d5245e368180779f357051
""")

def sm(cid, txt, kb=None):
    try:
        p = {"chat_id": cid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/sendMessage", json=p, timeout=3)
    except: pass

def em(cid, mid, txt, kb=None):
    try:
        p = {"chat_id": cid, "message_id": mid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/editMessageText", json=p, timeout=3)
    except: pass

def ac(qid, txt, alert=False):
    try: session.post(f"{API}/answerCallbackQuery", json={"callback_query_id": qid, "text": txt, "show_alert": alert}, timeout=2)
    except: pass

def dl(url, is_video=True):
    fmt = 'best[height<=480]/best' if is_video else 'bestaudio/best'
    opts = {
        'outtmpl': 'dl/%(title).60s.%(ext)s',
        'format': fmt,
        'merge_output_format': 'mp4' if is_video else None,
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'retries': 3, 'socket_timeout': 25,
        'cookiefile': COOKIES_FILE,
        'user_agent': 'Mozilla/5.0'
    }
    if not is_video:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info: return None, "فشل"
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            exts = ['mp4','mkv','webm'] if is_video else ['mp3']
            for ext in exts:
                if os.path.exists(f"{base}.{ext}"): path = f"{base}.{ext}"; break
        if os.path.exists(path):
            return path, info.get('title', 'بدون عنوان')
        return None, "الملف غير موجود"
    except Exception as e:
        err = str(e)
        if "private" in err.lower(): return None, "المحتوى خاص"
        if "login" in err.lower(): return None, "يتطلب تسجيل دخول"
        return None, err[:200]

def save_urls():
    try:
        with open('dl/urls.json', 'w') as f: json.dump(urls, f)
    except: pass

def load_urls():
    global urls
    try:
        with open('dl/urls.json', 'r') as f: urls = json.load(f)
    except: urls = {}

def process(u):
    if "callback_query" in u:
        q = u["callback_query"]
        cid = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        d = q["data"]
        
        if d.startswith("v_"):
            key = d[2:]
            if key not in urls: ac(q["id"], "❌ انتهت الجلسة", True); return
            ac(q["id"], "⏳ تحميل فيديو...")
            em(cid, mid, "⏳ **تحميل الفيديو...**")
            path, title = dl(urls[key], True)
            if path and os.path.exists(path):
                size = os.path.getsize(path)//(1024*1024)
                if size > 50:
                    em(cid, mid, f"⚠️ كبير ({size}MB)\nجرب الصوت")
                    try: os.remove(path)
                    except: pass
                else:
                    try:
                        with open(path,'rb') as f:
                            session.post(f"{API}/sendVideo", data={"chat_id":cid,"supports_streaming":True,"caption":f"✅ {title}\n📦 {size}MB"}, files={"video":f}, timeout=120)
                        em(cid, mid, f"✅ **تم!**\n📹 {title}")
                    except: em(cid, mid, "❌ فشل الإرسال")
                    try: os.remove(path)
                    except: pass
            else: em(cid, mid, f"❌ {title}")
        
        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls: ac(q["id"], "❌ انتهت الجلسة", True); return
            ac(q["id"], "⏳ تحميل صوت...")
            em(cid, mid, "⏳ **تحميل الصوت...**")
            path, title = dl(urls[key], False)
            if path and os.path.exists(path):
                try:
                    with open(path,'rb') as f:
                        session.post(f"{API}/sendAudio", data={"chat_id":cid,"caption":f"🎵 {title}"}, files={"audio":f}, timeout=120)
                    em(cid, mid, f"✅ **تم!**\n🎵 {title}")
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
            save_urls()
            kb = json.dumps({"inline_keyboard": [[
                {"text": "🎥 تحميل فيديو", "callback_data": f"v_{key}"},
                {"text": "🎵 تحميل صوت MP3", "callback_data": f"a_{key}"}
            ]]})
            sm(cid, "✅ **تم استلام الرابط**\n\n**اختر نوع التحميل:**", kb)

def run():
    global offset
    load_urls()
    print("⚡ البوت يعمل...")
    while True:
        try:
            r = session.get(f"{API}/getUpdates", params={"offset":offset+1,"timeout":10}, timeout=15)
            if r.status_code != 200: time.sleep(1); continue
            for u in r.json().get("result", []):
                offset = u["update_id"]
                process(u)
        except: time.sleep(1)

if __name__ == "__main__":
    run()
