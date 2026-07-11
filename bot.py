import os
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import queue
import threading

# --- الإعدادات الأساسية ---
TOKEN = os.environ.get("TOKEN", "8952358620:AAFhrUkYVJvvVAnrWKiCuy7TR122Vt7ilXg")
bot = telebot.TeleBot(TOKEN)
DL_DIR = "/tmp/dl"
os.makedirs(DL_DIR, exist_ok=True)

# قاموس لحفظ روابط المستخدمين مؤقتاً
user_urls = {}

# --- نظام الطوابير ---
dl_queue = queue.Queue()

def process_queue():
    """عامل يعمل بالخلفية يسحب الطلبات من الطابور وينفذها بالترتيب"""
    while True:
        task = dl_queue.get() # سحب أول طلب في الطابور
        cid = task['cid']
        mid = task['mid']
        url = task['url']
        dl_type = task['type']

        try:
            bot.edit_message_text("⏳ بدأ دورك! جاري المعالجة والتحميل الآن...", cid, mid)
            
            # استدعاء دالة التحميل
            file_path = download_media(url, cid, type=dl_type)
            
            if file_path and os.path.exists(file_path):
                # فحص حجم الملف (حد تليجرام 50 ميجا)
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                if file_size > 49.5:
                    bot.edit_message_text(f"⚠️ حجم الملف ({file_size:.1f} MB) يتجاوز الحد المسموح لتليجرام (50 MB).", cid, mid)
                else:
                    bot.edit_message_text("🚀 جاري الرفع إلى تليجرام...", cid, mid)
                    try:
                        with open(file_path, 'rb') as f:
                            if dl_type == "audio":
                                bot.send_audio(cid, f, caption="تم التحميل بواسطة @B43lB")
                            else:
                                bot.send_video(cid, f, caption="تم التحميل بواسطة @B43lB")
                        bot.delete_message(cid, mid) # مسح رسالة "جاري الرفع" بعد الانتهاء
                    except Exception as e:
                        bot.send_message(cid, "❌ حدث خطأ أثناء الرفع إلى تليجرام.")
                        
                # حذف الملف من السيرفر لتوفير المساحة
                try: os.remove(file_path)
                except: pass
            else:
                bot.edit_message_text("❌ فشل التحميل! الرابط قد يكون خاصاً، أو الموقع قام بتغيير حمايته.", cid, mid)
                
        except Exception as e:
            print(f"Queue Error: {e}")
            try: bot.edit_message_text("❌ حدث خطأ غير متوقع أثناء المعالجة.", cid, mid)
            except: pass
            
        finally:
            dl_queue.task_done() # إخبار الطابور بانتهاء الطلب للانتقال للذي يليه

# تشغيل الطابور في مسار (Thread) منفصل
threading.Thread(target=process_queue, daemon=True).start()


# --- رسائل البوت ---
START_MSG = """👋 أهلاً بك في بوت التحميل المطور!
📩 أرسل أي رابط فيديو (يوتيوب، تيك توك، انستغرام، تويتر، بنترست...)
🎥 وسأقوم بتحميله لك فوراً.
المالك ✓ @B43lB"""

# --- دالة التحميل الذكية ---
def download_media(url, cid, type="video"):
    file_id = f"{cid}_{int(time.time())}"
    
    ydl_opts = {
        'outtmpl': f'{DL_DIR}/{file_id}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # هيدرز قوية لتخطي حظر تيك توك ويوتيوب
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        'extractor_args': {'tiktok': {'app_version': '20.2.1'}}
    }

    if type == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        # تحميل فيديو بصيغة mp4 متوافقة مع تليجرام
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if type == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
            return filename
    except Exception as e:
        print(f"Error in yt_dlp: {e}")
        return None

# --- الرد على /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, START_MSG)

# --- الرد على أي رابط ---
@bot.message_handler(func=lambda message: message.text and message.text.startswith('http'))
def handle_url(message):
    cid = message.chat.id
    user_urls[cid] = message.text  # حفظ الرابط
    
    # صنع أزرار شفافة (Inline Keyboard)
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎬 فيديو (MP4)", callback_data="dl_video"))
    markup.row(InlineKeyboardButton("🎵 صوت فقط (MP3)", callback_data="dl_audio"))
    
    bot.reply_to(message, "📥 ماذا تريد أن تحمل من هذا الرابط؟", reply_markup=markup)

# --- التعامل مع ضغطات الأزرار (إضافة للطابور) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def handle_download(call):
    cid = call.message.chat.id
    mid = call.message.message_id
    url = user_urls.get(cid)
    
    if not url:
        bot.edit_message_text("❌ عذراً، انتهت صلاحية الرابط. أرسله من جديد.", cid, mid)
        return

    dl_type = "audio" if call.data == "dl_audio" else "video"
    
    # معرفة رقم المستخدم في الطابور
    queue_position = dl_queue.qsize() + 1
    
    bot.edit_message_text(f"✅ تمت إضافتك للطابور.\nأنت رقم ({queue_position}) في الانتظار...", cid, mid)
    
    # رمي الطلب في الطابور بدل معالجته فوراً
    dl_queue.put({
        'cid': cid,
        'mid': mid,
        'url': url,
        'type': dl_type
    })

# --- تشغيل البوت باستمرار ---
print("✅ البوت يعمل الآن مع نظام الطوابير...")
bot.infinity_polling()
