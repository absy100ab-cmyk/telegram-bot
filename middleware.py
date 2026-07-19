import os
import requests

# قراءة معرف القناة من متغيرات ريلواي
CHANNEL_ID = os.environ.get("CHANNEL_ID")

def is_subscribed(user_id, token):
    # إذا لم يتم تعيين قناة في ريلواي، يتخطى الفحص تلقائياً لضمان عدم توقف البوت
    if not CHANNEL_ID:
        return True
        
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    params = {"chat_id": CHANNEL_ID, "user_id": user_id}
    
    try:
        response = requests.get(url, params=params).json()
        if response.get("ok"):
            status = response["result"]["status"]
            # إذا كان العضو بالقروب/القناة (أدمن، مالك، أو عضو عادي)
            if status in ["creator", "administrator", "member"]:
                return True
        return False
    except Exception as e:
        print(f"Middleware Error: {e}")
        return True # تجنباً لتوقف البوت لو علق سيرفر تليجرام
