import requests
import time
import os
import json
import hashlib
import re
import yt_dlp

TOKEN = os.environ.get("TOKEN", "8952358620:AAFhrUkYVJvvVAnrWKiCuy7TR122Vt7ilXg")
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
DL_DIR = "/tmp/dl"
os.makedirs(DL_DIR, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"})

START_MSG = """👋 أهلاً بك!
📩 أرسل رابط الفيديو للتحميل.
🎥 اختر الجودة أو 🎵 صوت MP3.
📱 يوتيوب | تيك توك | انستغرام | تويتر | فيسبوك | بنترست
المالك ✓ @B43lB"""

COOKIES_FILE = "/tmp/dl/cookies.txt"
with open(COOKIES_FILE, 'w') as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tCONSENT\tYES+cb\n")
    f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tGPS\t1\n")

def sm(cid, txt, kb=None):
    try:
        p = {"chat_id": cid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        return session.post(f"{API}/sendMessage", json=p, timeout=5).json()
    except: return None

def em(cid, mid, txt, kb=None):
    try:
        p = {"chat_id": cid, "message_id": mid, "text": txt[:4000], "parse_mode": "Markdown"}
        if kb: p["reply_markup"] = kb
        session.post(f"{API}/editMessageText", json=p, timeout=5)
    except: pass

def send_video(cid, filepath, caption=""):
    try:
        with open(filepath, 'rb') as video:
            files = {'video': video}
            data = {'chat_id': cid, 'caption': caption}
            return session.post(f"{API}/sendVideo", data=data, files=files, timeout=60).json()
    except Exception as e:
        print(f"Error sending video: {e}")
        return None

def send_audio(cid, filepath, caption=""):
    try:
        with open(filepath, 'rb') as audio:
            files = {'audio': audio}
            data = {'chat_id': cid, 'caption': caption}
            return session.post(f"{API}/sendAudio", data=data, files=files, timeout=60).json()
    except Exception as e:
        print(f"Error sending audio: {e}")
        return None

# === دالة التحميل الذكية باستخدام yt_dlp ===
def download_media(url, cid, quality="720", audio_only=False):
    # توليد اسم ملف فريد باستخدام الـ timestamp والـ chat_id
    file_id = f"{cid}_{int(time.time())}"
    
    ydl_opts = {
        'outtmpl': f'{DL_DIR}/{file_id}.%(ext)s',
        'cookiefile': COOKIES_FILE,
        'quiet': True,
        'no_warnings': True,
    }

    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # اختيار الجودة المطلوبة أو أقرب جودة لها بحيث لا تتعدى المسموح
        ydl_opts.update({
            'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best',
            'merge_output_format': 'mp4'
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # إذا كان صوت، الامتداد سيتحول إلى mp3 تلقائياً بسبب الـ postprocessor
            if audio_only:
                filename = os.path.splitext(filename)[0] + ".mp3"
            elif not os.path.exists(filename):
                # في بعض الأحيان يتم دمج الفيديو بصيغة mp4 تلقائياً
                filename = os.path.splitext(filename)[0] + ".mp4"
                
            return filename
    except Exception as e:
        print(f"Download error: {e}")
        return None

# === دالة فحص التحديثات الأساسية (Long Polling) ===
def main_loop():
    global offset
    print("Bot started...")
    while True:
        try:
            r = session.get(f"{API}/getUpdates", json={"offset": offset, "timeout": 20}, timeout=25).json()
            if not r.get("ok"): continue
            
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                
                # التعامل مع الرسائل النصية
                if "message" in u and "text" in u["message"]:
                    msg = u["message"]
                    cid = msg["chat"]["id"]
                    txt = msg["text"]
                    
                    if txt == "/start":
                        sm(cid, START_MSG)
                    elif txt.startswith("http"):
                        # حفظ الرابط مؤقتاً للمستخدم (تطوير بسيط لأجل الأزرار)
                        urls[cid] = txt
                        kb = {
                            "inline_keyboard": [
                                [{"text": "🎬 فيديو 720p", "callback_data": "vid_720"}, {"text": "🎬 فيديو 480p", "callback_data": "vid_480"}],
                                [{"text": "🎵 صوت MP3", "callback_data": "aud_mp3"}]
                            ]
                        }
                        sm(cid, "📥 اختر صيغة التحميل المناسبة:", kb)
                
                # التعامل مع ضغطات الأزرار (Callback Queries)
                elif "callback_query" in u:
                    cb = u["callback_query"]
                    cid = cb["message"]["chat"]["id"]
                    mid = cb["message"]["message_id"]
                    data = cb["data"]
                    
                    url = urls.get(cid)
                    if not url:
                        em(cid, mid, "❌ انتهت صلاحية الرابط، أرسله مجدداً.")
                        continue
                        
                    em(cid, mid, "⏳ جاري التحميل والمعالجة... قد يستغرق ذلك دقيقة.")
                    
                    if data == "aud_mp3":
                        file = download_media(url, cid, audio_only=True)
                        if file and os.path.exists(file):
                            em(cid, mid, "🚀 جاري الرفع إلى تليجرام...")
                            send_audio(cid, file, "تم التحميل بواسطة @B43lB")
                            try: os.remove(file)
                            except: pass
                        else:
                            em(cid, mid, "❌ فشل تحميل الصوت. تأكد من الرابط أو جرب لاحقاً.")
                            
                    elif data.startswith("vid_"):
                        quality = data.split("_")[1]
                        file = download_media(url, cid, quality=quality, audio_only=False)
                        if file and os.path.exists(file):
                            # فحص الحجم قبل الرفع (تليجرام ليميت = 50MB للـ API العادي)
                            if os.path.getsize(file) > 49 * 1024 * 1024:
                                em(cid, mid, "⚠️ الملف كبير جداً (أكبر من 50 ميجا). الـ API المجاني لا يدعم رفعه.")
                            else:
                                em(cid, mid, "🚀 جاري الرفع إلى تليجرام...")
                                send_video(cid, file, f"تم التحميل بجودة {quality}p ✓")
                            try: os.remove(file)
                            except: pass
                        else:
                            em(cid, mid, "❌ فشل تحميل الفيديو. تأكد من صلاحية الرابط.")
                            
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main_loop()
