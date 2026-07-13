import os
import time
import queue
import random
import threading
import yt_dlp
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================================
# إعدادات البوت الأساسية
# ============================================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # استبدل بالتوكن الخاص بك
START_MSG = """
🎬 **مرحباً بك في بوت التحميل!**

أرسل رابط من:
• تيك توك (TikTok)
• يوتيوب (YouTube)
• انستغرام (Instagram)
• فيسبوك (Facebook)

سأعطيك خيارات التحميل المناسبة!
"""

# ============================================
# المتغيرات العامة
# ============================================
dl_queue = queue.Queue()
user_urls = {}
DOWNLOAD_PATH = "downloads"
COOKIES_FILE = "cookies.txt"  # ملف الكوكيز القديم

# إنشاء مجلد التحميلات إذا لم يكن موجوداً
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ============================================
# قائمة User-Agents متنوعة
# ============================================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

# ============================================
# دالة للحصول على User-Agent عشوائي
# ============================================
def get_random_user_agent():
    return random.choice(USER_AGENTS)

# ============================================
# إعدادات yt-dlp مع الكوكيز القديمة
# ============================================
def get_ydl_opts(dl_type):
    """
    إعدادات yt-dlp للتحميل باستخدام الكوكيز القديمة
    """
    
    # التحقق من وجود ملف الكوكيز
    if os.path.exists(COOKIES_FILE):
        print(f"✅ تم العثور على ملف الكوكيز: {COOKIES_FILE}")
        cookies_option = {'cookiefile': COOKIES_FILE}
    else:
        print(f"⚠️ ملف الكوكيز {COOKIES_FILE} غير موجود، سيتم التحميل بدون كوكيز")
        cookies_option = {}
    
    # الإعدادات الأساسية
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'file_access_retries': 10,
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
        'http_headers': {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        },
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
    
    # إضافة الكوكيز القديمة
    ydl_opts.update(cookies_option)
    
    # ============================================
    # إعدادات حسب نوع التحميل
    # ============================================
    if dl_type == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:  # فيديو
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    
    return ydl_opts

# ============================================
# دالة التحميل مع إعادة المحاولة
# ============================================
def download_with_retry(url, dl_type, max_retries=3):
    """تحميل الملف مع إعادة المحاولة في حالة الفشل"""
    
    for attempt in range(max_retries):
        try:
            print(f"محاولة {attempt + 1} لتحميل: {url}")
            print(f"📁 استخدام كوكيز من: {COOKIES_FILE if os.path.exists(COOKIES_FILE) else 'بدون كوكيز'}")
            
            # الحصول على الإعدادات مع الكوكيز
            ydl_opts = get_ydl_opts(dl_type)
            
            # تغيير User-Agent في كل محاولة
            ydl_opts['http_headers']['User-Agent'] = get_random_user_agent()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if dl_type == "audio":
                    base, _ = os.path.splitext(filename)
                    filename = base + ".mp3"
                
                if os.path.exists(filename):
                    return filename
                else:
                    raise Exception("الملف لم يتم إنشاؤه")
                    
        except Exception as e:
            print(f"❌ فشلت المحاولة {attempt + 1}: {e}")
            
            if attempt == max_retries - 1:
                raise
            
            time.sleep(2 ** attempt)
    
    return None

# ============================================
# التحقق من صحة ملف الكوكيز
# ============================================
def check_cookies_file():
    """التحقق من صحة وتنسيق ملف الكوكيز"""
    
    if not os.path.exists(COOKIES_FILE):
        print(f"⚠️ ملف الكوكيز غير موجود: {COOKIES_FILE}")
        print("📝 يمكنك إنشاء ملف cookies.txt باستخدام:")
        print("1. إضافة 'Get cookies.txt' في المتصفح")
        print("2. تصدير الكوكيز من الموقع المطلوب")
        return False
    
    # قراءة أول سطرين للتحقق من التنسيق
    try:
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # التحقق من وجود كوكيز (أكثر من سطر تعليق)
            cookie_lines = [line for line in lines if not line.startswith('#') and line.strip()]
            
            if len(cookie_lines) == 0:
                print("⚠️ ملف الكوكيز فارغ!")
                return False
            
            # طباعة معلومات عن الكوكيز
            print(f"✅ ملف الكوكيز يحتوي على {len(cookie_lines)} كوكيز")
            
            # عرض مثال لأول كوكيز
            if cookie_lines:
                parts = cookie_lines[0].split('\t')
                if len(parts) >= 7:
                    print(f"📝 مثال: Domain={parts[0]}, Name={parts[5]}")
            
            return True
            
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف الكوكيز: {e}")
        return False

# ============================================
# دالة معالجة الطابور
# ============================================
def process_queue():
    """معالج الطابور - يعمل في خيط منفصل"""
    
    while True:
        if not dl_queue.empty():
            task = dl_queue.get()
            cid = task['cid']
            mid = task['mid']
            url = task['url']
            dl_type = task['type']
            
            try:
                bot.edit_message_text("⏳ جاري التحميل... قد يستغرق هذا بضع ثوانٍ", cid, mid)
                
                filename = download_with_retry(url, dl_type)
                
                if filename and os.path.exists(filename):
                    with open(filename, 'rb') as f:
                        if dl_type == "audio":
                            bot.send_audio(cid, f, caption="🎵 تم التحميل بنجاح!")
                        else:
                            bot.send_video(cid, f, caption="🎬 تم التحميل بنجاح!")
                    
                    os.remove(filename)
                    bot.edit_message_text("✅ تم التحميل وإرساله بنجاح!", cid, mid)
                else:
                    bot.edit_message_text("❌ فشل التحميل. يرجى المحاولة مرة أخرى لاحقاً.", cid, mid)
                    
            except Exception as e:
                print(f"❌ خطأ في معالجة الطابور: {e}")
                error_msg = f"❌ حدث خطأ أثناء التحميل: {str(e)[:100]}"
                bot.edit_message_text(error_msg, cid, mid)
            
            dl_queue.task_done()
        
        time.sleep(0.5)

# ============================================
# بدء تشغيل معالج الطابور
# ============================================
threading.Thread(target=process_queue, daemon=True).start()

# ============================================
# إنشاء البوت
# ============================================
bot = telebot.TeleBot(BOT_TOKEN)

# ============================================
# أمر /start
# ============================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, START_MSG, parse_mode='Markdown')

# ============================================
# التعامل مع الروابط
# ============================================
@bot.message_handler(func=lambda message: message.text and message.text.startswith('http'))
def handle_url(message):
    cid = message.chat.id
    url = message.text.strip()
    
    user_urls[cid] = url
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎬 فيديو (MP4)", callback_data="dl_video"),
        InlineKeyboardButton("🎵 صوت فقط (MP3)", callback_data="dl_audio")
    )
    
    bot.reply_to(message, "📥 ماذا تريد أن تحمل من هذا الرابط؟", reply_markup=markup)

# ============================================
# التعامل مع ضغطات الأزرار
# ============================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def handle_download(call):
    cid = call.message.chat.id
    mid = call.message.message_id
    url = user_urls.get(cid)
    
    if not url:
        bot.edit_message_text("❌ عذراً، انتهت صلاحية الرابط. أرسله من جديد.", cid, mid)
        return
    
    dl_type = "audio" if call.data == "dl_audio" else "video"
    queue_position = dl_queue.qsize() + 1
    
    bot.edit_message_text(
        f"✅ تمت إضافتك للطابور.\nأنت رقم ({queue_position}) في الانتظار...",
        cid, mid
    )
    
    dl_queue.put({
        'cid': cid,
        'mid': mid,
        'url': url,
        'type': dl_type
    })

# ============================================
# تشغيل البوت
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 تشغيل بوت التحميل...")
    print("=" * 50)
    
    # التحقق من ملف الكوكيز
    cookies_status = check_cookies_file()
    
    print(f"📁 مجلد التحميلات: {DOWNLOAD_PATH}")
    print(f"🌐 عدد User-Agents: {len(USER_AGENTS)}")
    print(f"🍪 حالة الكوكيز: {'✅ مفعلة' if cookies_status else '⚠️ معطلة'}")
    print(f"📄 ملف الكوكيز: {COOKIES_FILE if os.path.exists(COOKIES_FILE) else 'غير موجود'}")
    print("=" * 50)
    print("✅ البوت يعمل الآن مع نظام الطوابير...")
    
    bot.infinity_polling()
