import requests
import time
import os
import json
import hashlib
import re
import random
import shutil
import logging
import yt_dlp

# ===================================================================
# التوكن: يُقرأ الآن من متغير بيئة (Environment Variable)
# ===================================================================
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "❌ لم يتم العثور على التوكن.\n"
        "حدد متغير البيئة BOT_TOKEN قبل تشغيل البوت، مثال:\n"
        '  export BOT_TOKEN="ضع_التوكن_هنا"'
    )

API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}

DL_DIR = "/tmp/dl"
os.makedirs(DL_DIR, exist_ok=True)
session = requests.Session()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("bot")

START_MSG = """👋 أهلاً بك!
📩 أرسل رابط الفيديو للتحميل.
🎥 اختر الجودة أو 🎵 صوت MP3.
📱 يوتيوب | تيك توك | انستغرام | تويتر | فيسبوك | بنترست
المالك ✓ @B43lB"""

HELP_MSG = """🆘 أرسل رابط الفيديو ثم اختر الجودة أو الصوت."""
ABOUT_MSG = """🤖 بوت التحميل v5\n🎥 144p-1080p | 🎵 MP3\n👨‍💻 @B43lB"""
SETTINGS_MSG = """⚙️ الجودة: 144p-1080p | الصوت: MP3"""

# ===== كوكيز تيك توك وبنترست ويوتيوب =====
COOKIES_FILE = os.path.join(DL_DIR, "cookies.txt")
COOKIES_CONTENT = """# Netscape HTTP Cookie File
.tiktok.com	TRUE	/	TRUE	1735689600	tt_webid	v1_abc123def456
.tiktok.com	TRUE	/	TRUE	1735689600	sessionid	abc123xyz789
.pinterest.com	TRUE	/	TRUE	1735689600	csrftoken	csrf_token_abc123
.youtube.com	TRUE	/	TRUE	0	CONSENT	YES+cb
"""

with open(COOKIES_FILE, "w") as f:
    f.write(COOKIES_CONTENT)

log.info(f"✅ تم حفظ الكوكيز في {COOKIES_FILE}")

FFMPEG_OK = shutil.which("ffmpeg") is not None
if not FFMPEG_OK:
    log.warning("⚠️ لم يتم العثور على ffmpeg على النظام. تحميل الصوت (MP3) لن يعمل.")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def escape_markdown(text):
    """تنظيف النصوص لمنع أخطاء الـ Markdown في تليجرام"""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def sm(cid, txt, kb=None):
    try:
        p = {"chat_id": cid, "text": txt, "parse_mode": "MarkdownV2"}
        if kb:
            p["reply_markup"] = kb
        session.post(f"{API}/sendMessage", json=p, timeout=5)
    except Exception as e:
        log.error(f"sendMessage failed: {e}")

def em(cid, mid, txt, kb=None):
    try:
        p = {"chat_id": cid, "message_id": mid, "text": txt, "parse_mode": "MarkdownV2"}
        if kb:
            p["reply_markup"] = kb
        session.post(f"{API}/editMessageText", json=p, timeout=5)
    except Exception as e:
        log.error(f"editMessageText failed: {e}")

def ac(qid, txt, alert=False):
    try:
        session.post(
            f"{API}/answerCallbackQuery",
            json={"callback_query_id": qid, "text": txt, "show_alert": alert},
            timeout=5,
        )
    except Exception as e:
        log.error(f"answerCallbackQuery failed: {e}")

def download(url, quality="720", audio=False):
    if "pinterest.com" in url.lower() or "pin.it" in url.lower():
        try:
            h = {"User-Agent": random.choice(USER_AGENTS)}
            r = session.get(url, headers=h, timeout=15)
            html = r.text
            v = re.findall(r'"(https?://[^"]*\.mp4[^"]*)"', html)
            if v:
                vurl = v[0].replace("\\", "")
                path = f"{DL_DIR}/p_{int(time.time())}.mp4"
                r2 = session.get(vurl, headers=h, timeout=120)
                with open(path, "wb") as f:
                    f.write(r2.content)
                if os.path.exists(path) and os.path.getsize(path) > 10000:
                    return path, "Pinterest Video"
            return None, "لم يتم العثور على محتوى قابل للتحميل"
        except Exception as e:
            return None, str(e)[:200]

    if audio and not FFMPEG_OK:
        return None, "ffmpeg غير مثبت على السيرفر"

    fmt = "bestaudio/best" if audio else f"best[height<={quality}]/best"
    opts = {
        "outtmpl": f"{DL_DIR}/%(title).60s.%(ext)s",
        "format": fmt,
        "merge_output_format": None if audio else "mp4",
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "retries": 5,
        "socket_timeout": 30,
        "cookiefile": COOKIES_FILE,
        "http_headers": {"User-Agent": random.choice(USER_AGENTS)},
    }

    if audio:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info:
            return None, "فشل في استخراج البيانات"

        path = ydl.prepare_filename(info)
        if audio:
            path = os.path.splitext(path)[0] + ".mp3"

        if not os.path.exists(path):
            base = os.path.splitext(path)[0]
            for e in (["mp3"] if audio else ["mp4", "mkv", "webm"]):
                if os.path.exists(f"{base}.{e}"):
                    path = f"{base}.{e}"
                    break

        if os.path.exists(path):
            return path, info.get("title", "Download")
        return None, "الملف غير موجود"
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
                ac(q["id"], "انتهت صلاحية الرابط")
                return
            ac(q["id"], "جاري التحميل...")
            em(cid, mid, f"⏳ جاري تحميل جودة {quality}p...")
            path, title = download(urls[key], quality)
            
            if path and os.path.exists(path):
                size = os.path.getsize(path) // (1024 * 1024)
                if size > 50:
                    em(cid, mid, escape_markdown(f"⚠️ الملف كبير جدًا ({size}MB) - الحد المسموح به للبوتات هو 50MB فقط."))
                else:
                    try:
                        with open(path, "rb") as f:
                            cleaned_title = escape_markdown(title)
                            if path.endswith((".jpg", ".png")):
                                session.post(
                                    f"{API}/sendPhoto",
                                    data={"chat_id": cid, "caption": f"✅ {cleaned_title}"},
                                    files={"photo": f},
                                    timeout=300,
                                )
                            else:
                                session.post(
                                    f"{API}/sendVideo",
                                    data={
                                        "chat_id": cid,
                                        "supports_streaming": True,
                                        "caption": f"✅ {cleaned_title}\n{size}MB | {quality}p",
                                    },
                                    files={"video": f},
                                    timeout=300,
                                )
                        em(cid, mid, f"✅ {cleaned_title}")
                    except Exception as e:
                        em(cid, mid, escape_markdown(f"❌ فشل الإرسال: {str(e)[:100]}"))
                try:
                    os.remove(path)
                except:
                    pass
            else:
                em(cid, mid, escape_markdown(f"❌ فشل: {title}"))

        elif d.startswith("a_"):
            key = d[2:]
            if key not in urls:
                ac(q["id"], "انتهت صلاحية الرابط")
                return
            ac(q["id"], "جاري تحميل الصوت...")
            em(cid, mid, "⏳ جاري استخراج وتحميل الصوت...")
            path, title = download(urls[key], audio=True)
            if path and os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        session.post(
                            f"{API}/sendAudio",
                            data={"chat_id": cid, "caption": f"🎵 {escape_markdown(title)}"},
                            files={"audio": f},
                            timeout=300,
                        )
                    em(cid, mid, f"✅ {escape_markdown(title)}")
                except Exception as e:
                    em(cid, mid, escape_markdown(f"❌ فشل إرسال الصوت: {str(e)[:100]}"))
                try:
                    os.remove(path)
                except:
                    pass
            else:
                em(cid, mid, escape_markdown(f"❌ فشل: {title}"))
        return

    if "message" in u and "text" in u["message"]:
        m = u["message"]
        cid = m["chat"]["id"]
        txt = m["text"].strip()
        
        if txt == "/start":
            sm(cid, escape_markdown(START_MSG))
        elif txt == "/help":
            sm(cid, escape_markdown(HELP_MSG))
        elif txt == "/about":
            sm(cid, escape_markdown(ABOUT_MSG))
        elif txt == "/settings":
            sm(cid, escape_markdown(SETTINGS_MSG))
        elif txt.startswith("http"):
            key = hashlib.md5(txt.encode()).hexdigest()[:8]
            urls[key] = txt
            kb = json.dumps({
                "inline_keyboard": [
                    [
                        {"text": "🎥 144p", "callback_data": f"q_{key}_144"},
                        {"text": "🎥 360p", "callback_data": f"q_{key}_360"},
                    ],
                    [
                        {"text": "🎥 480p", "callback_data": f"q_{key}_480"},
                        {"text": "🎥 720p", "callback_data": f"q_{key}_720"},
                    ],
                    [{"text": "🎥 1080p", "callback_data": f"q_{key}_1080"}],
                    [{"text": "🎵 صوت MP3", "callback_data": f"a_{key}"}],
                ]
            })
            sm(cid, escape_markdown("✅ تم استلام الرابط بنجاح\nاختر الجودة المطلوبة:"), kb)

def run():
    global offset
    log.info("⚡ البوت يعمل الآن بنجاح وبدون مشاكل...")
    while True:
        try:
            r = session.get(f"{API}/getUpdates", params={"offset": offset + 1, "timeout": 15}, timeout=20)
            if r.status_code != 200:
                time.sleep(2)
                continue
            for u in r.json().get("result", []):
                offset = u["update_id"]
                try:
                    process(u)
                except Exception as e:
                    log.error(f"Error processing update: {e}")
        except Exception as e:
            log.error(f"Connection error in loop: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run()
