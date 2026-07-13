#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import queue
import random
import threading
import logging
from datetime import datetime

# تثبيت التبعيات تلقائياً
def install_packages():
    packages = ['pyTelegramBotAPI', 'yt-dlp']
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"📦 جاري تثبيت {package}...")
            os.system(f"{sys.executable} -m pip install {package}")

install_packages()

# استيراد المكتبات بعد التأكد من تثبيتها
import yt_dlp
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================================
# إعدادات التسجيل (Logging)
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# إعدادات البوت
# ============================================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ⚠️ استبدل بالتوكن الخاص بك

START_MSG = """
🎬 **مرحباً بك في بوت التحميل!**

📥 أرسل رابط من:
• تيك توك (TikTok)
• يوتيوب (YouTube)  
• انستغرام (Instagram)
• فيسبوك (Facebook)
• تويتر (Twitter/X)

سأعطيك خيارات التحميل المناسبة!
"""

# ============================================
# المتغيرات العامة
# ============================================
dl_queue = queue.Queue()
user_urls = {}
DOWNLOAD_PATH = "downloads"
COOKIES_FILE = "cookies.txt"

# إنشاء المجلدات
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ============================================
# قائمة User-Agents
# ============================================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

# ============================================
# التحقق من ملف الكوكيز
# ============================================
def check_cookies():
    """التحقق من وجود وصلاحية ملف الكوكيز"""
    if os.path.exists(COOKIES_FILE):
        try:
            with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'tiktok' in content.lower() or 'youtube' in content.lower():
                    logger.info(f"✅ تم العثور على كوكيز للمواقع المطلوبة")
                    return True
                else:
                    logger.warning("⚠️ ملف الكوكيز لا يحتوي على كوكيز للمواقع المطلوبة")
                    return False
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة ملف الكوكيز: {e}")
            return False
    else:
        logger.warning("⚠️ ملف الكوكيز غير موجود")
        return False

# ============================================
# إعدادات yt-dlp
# ============================================
def get_ydl_opts(dl_type):
    """إعدادات yt-dlp للتحميل"""
    
    # الإعدادات الأساسية
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s_%(id)s.%(ext)s'),
        'http_headers': {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        },
        'extractor_args': {
            'tiktok': {
                'app_version': ['34.1.2'],
                'device_type': ['iPhone13,3'],
            },
            'youtube': {
                'player_client': ['android'],
            }
        }
    }
    
    # إضافة الكوكيز إذا كانت موجودة
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
        logger.info(f"🍪 استخدام كوكيز من: {COOKIES_FILE}")
    
    # إعدادات حسب نوع التحميل
    if dl_type == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    
    return ydl_opts

# ============================================
# دالة التحميل الرئيسية
# ============================================
def download_media(url, dl_type):
    """تحميل الميديا من الرابط"""
    try:
        logger.info(f"📥 بدء تحميل: {url} (نوع: {dl_type})")
        
        ydl_opts = get_ydl_opts(dl_type)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # محاولة استخراج المعلومات
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                logger.error(f"❌ فشل استخراج المعلومات: {e}")
                # محاولة بدون كوكيز
                if 'cookiefile' in ydl_opts:
                    del ydl_opts['cookiefile']
                    logger.info("🔄 محاولة التحميل بدون كوكيز...")
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                        info = ydl2.extract_info(url, download=True)
            
            # تحديد اسم الملف
            filename = ydl.prepare_filename(info)
            
            if dl_type == "audio":
                base, _ = os.path.splitext(filename)
                filename = base + ".mp3"
            
            if os.path.exists(filename):
                logger.info(f"✅ تم التحميل بنجاح: {filename}")
                return filename
            else:
                raise Exception("الملف لم يتم إنشاؤه")
                
    except Exception as e:
        logger.error(f"❌ خطأ في التحميل: {e}")
        raise

# ============================================
# معالج الطابور
# ============================================
def process_queue():
    """معالجة طابور التحميلات"""
    logger.info("🔄 بدء تشغيل معالج الطابور...")
    
    while True:
        try:
            if not dl_queue.empty():
                task = dl_queue.get()
                cid = task['cid']
                mid = task['mid']
                url = task['url']
                dl_type = task['type']
                
                try:
                    # تحديث حالة المستخدم
                    bot.edit_message_text("⏳ جاري التحميل...", cid, mid)
                    
                    # تحميل الملف
                    filename = download_media(url, dl_type)
                    
                    if filename and os.path.exists(filename):
                        # إرسال الملف
                        with open(filename, 'rb') as f:
                            if dl_type == "audio":
                                bot.send_audio(cid, f, caption="🎵 تم التحميل بنجاح!")
                            else:
                                bot.send_video(cid, f, caption="🎬 تم التحميل بنجاح!")
                        
                        # حذف الملف المؤقت
                        os.remove(filename)
                        bot.edit_message_text("✅ تم التحميل والإرسال!", cid, mid)
                    else:
                        bot.edit_message_text("❌ فشل التحميل. حاول مرة أخرى.", cid, mid)
                        
                except Exception as e:
                    error_msg = str(e)[:200]
                    logger.error(f"❌ خطأ في معالجة المهمة: {error_msg}")
                    bot.edit_message_text(f"❌ خطأ: {error_msg}", cid, mid)
                
                dl_queue.task_done()
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالج الطابور: {e}")
            time.sleep(1)

# ============================================
# بدء تشغيل البوت
# ============================================
logger.info("🚀 بدء تشغيل البوت...")

# التحقق من الكوكيز
cookies_status = check_cookies()

# إنشاء البوت
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    logger.info("✅ تم إنشاء البوت بنجاح")
except Exception as e:
    logger.error(f"❌ فشل إنشاء البوت: {e}")
    sys.exit(1)

# بدء معالج الطابور
threading.Thread(target=process_queue, daemon=True).start()

# ============================================
# أوامر البوت
# ============================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """الرد على أمر /start"""
    bot.reply_to(message, START_MSG, parse_mode='Markdown')
    logger.info(f"📱 مستخدم جديد: {message.chat.id}")

@bot.message_handler(commands=['status'])
def send_status(message):
    """التحقق من حالة البوت"""
    status = f"""
📊 **حالة البوت**:

📁 مجلد التحميل: `{DOWNLOAD_PATH}`
🍪 الكوكيز: `{'✅ مفعلة' if cookies_status else '❌ معطلة'}`
📋 عدد المهام في الطابور: `{dl_queue.qsize()}`
👥 عدد المستخدمين: `{len(user_urls)}`
🔄 عدد محاولات إعادة التحميل: `5`
    """
    bot.reply_to(message, status, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.startswith(('http://', 'https://')))
def handle_url(message):
    """التعامل مع الروابط"""
    cid = message.chat.id
    url = message.text.strip()
    
    # حفظ الرابط
    user_urls[cid] = url
    
    # أزرار التحميل
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎬 فيديو MP4", callback_data="dl_video"),
        InlineKeyboardButton("🎵 صوت MP3", callback_data="dl_audio")
    )
    
    bot.reply_to(message, "📥 اختر نوع التحميل:", reply_markup=markup)
    logger.info(f"📎 رابط جديد من {cid}: {url[:50]}...")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def handle_download(call):
    """التعامل مع أزرار التحميل"""
    cid = call.message.chat.id
    mid = call.message.message_id
    url = user_urls.get(cid)
    
    if not url:
        bot.edit_message_text("❌ انتهت صلاحية الرابط. أرسله من جديد.", cid, mid)
        return
    
    dl_type = "audio" if call.data == "dl_audio" else "video"
    queue_position = dl_queue.qsize() + 1
    
    # إضافة للطابور
    dl_queue.put({
        'cid': cid,
        'mid': mid,
        'url': url,
        'type': dl_type
    })
    
    bot.edit_message_text(
        f"✅ تمت الإضافة للطابور!\n"
        f"📋 رقمك: {queue_position}\n"
        f"⏳ سيتم التحميل قريباً...",
        cid, mid
    )
    
    logger.info(f"📥 إضافة مهمة للطابور: {cid} - {dl_type}")

# ============================================
# تشغيل البوت
# ============================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 تشغيل بوت التحميل")
    print("="*50)
    print(f"📁 مسار التحميل: {os.path.abspath(DOWNLOAD_PATH)}")
    print(f"🍪 حالة الكوكيز: {'✅ مفعلة' if cookies_status else '⚠️ معطلة'}")
    print(f"📄 ملف الكوكيز: {COOKIES_FILE if os.path.exists(COOKIES_FILE) else 'غير موجود'}")
    print("="*50)
    print("✅ البوت جاهز للعمل...\n")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"❌ توقف البوت: {e}")
        sys.exit(1)
