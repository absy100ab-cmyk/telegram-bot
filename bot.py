import os
import sys
import requests
import yt_dlp
import time
import json
import hashlib
import re
import random

# ==========================================
# 🎵 حل مشكلة الـ ffmpeg تلقائياً لتحويل الصوت إلى MP3
# ==========================================
try:
    import imageio_ffmpeg
    # نجلب المسار المباشر لملف الـ ffmpeg المدمج بالمكتبة
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    # نضيف المسار إلى متغيرات النظام ليراه yt-dlp فوراً
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    FFMPEG_PATH = None

# ==========================================
# 🔑 التوكن والـ API الأساسي للبوت
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0
urls = {}
os.makedirs("/tmp/dl", exist_ok=True)
session = requests.Session()

START_MSG = """👋 أهلاً بك!
أرسل رابط الفيديو للتحميل.
MP3 اختر الجودة أو 🎵 صوت.
🎵 تيك توك | انستغرام | تويتر | فيسبوك | بنترست | @B431B ✔️ المالك"""

def get_updates(offset):
    try:
        r = session.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 20}, timeout=25)
        if r.status_code == 200:
            return r.json().get("result", [])
    except Exception:
        pass
    return []

def send_msg(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        session.post(f"{API}/sendMessage", data=data)
    except Exception:
        pass

def send_video(chat_id, filepath, caption=""):
    try:
        with open(filepath, "rb") as f:
            session.post(f"{API}/sendVideo", data={"chat_id": chat_id, "caption": caption}, files={"video": f}, timeout=120)
    except Exception:
        pass

def send_audio(chat_id, filepath, caption=""):
    try:
        with open(filepath, "rb") as f:
            session.post(f"{API}/sendAudio", data={"chat_id": chat_id, "caption": caption}, files={"audio": f}, timeout=120)
    except Exception:
        pass

def edit_msg(chat_id, msg_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": msg_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        session.post(f"{API}/editMessageText", data=data)
    except Exception:
        pass

# ... بقية معالجات الروابط والتحميل مالتك مالت الـ yt-dlp تشتغل هنا تلقائياً ...
