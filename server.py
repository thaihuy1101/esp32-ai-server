import os
import io
import base64
from fastapi import FastAPI, Request, Response
import google.generativeai as genai
import io
from gtts import gTTS
import uvicorn

app = FastAPI()

# --- CẤU HÌNH API KEY ---
# Nhập API Key Gemini (Bảo mật: Lấy từ biến môi trường khi đưa lên Cloud)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("[!] CẢNH BÁO: Chưa cấu hình GEMINI_API_KEY trong Environment Variables!")

genai.configure(api_key=GEMINI_API_KEY)
try:
    print("[*] Danh sách các Model được hỗ trợ:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f" - {m.name}")
except Exception as e:
    print(f"[!] Lỗi khi lấy danh sách model: {e}")

model = genai.GenerativeModel('gemini-3.8-flash')



# Biến lưu trữ lịch sử trò chuyện tạm thời
chat_history = ""

@app.post("/chat")
async def chat(request: Request):
    global chat_history
    
    # 1. Nhận file WAV thô từ ESP32
    wav_bytes = await request.body()
    print(f"[*] Đã nhận {len(wav_bytes)} bytes âm thanh từ ESP32.")
    
    if len(wav_bytes) == 0:
        return Response(status_code=400, content="Không có dữ liệu âm thanh")

    try:
        import datetime
        
        # Lấy ngày giờ hiện tại
        days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        now_dt = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        now_str = f"{now_dt.strftime('%H:%M:%S')} {days[now_dt.weekday()]} ngày {now_dt.strftime('%d/%m/%Y')}"
        # Lấy thông tin môi trường từ ESP32
        temp_str = request.headers.get("X-Temperature", "Không xác định")
        hum_str = request.headers.get("X-Humidity", "Không xác định")
        
        # 2. Xây dựng Prompt và gửi lên Gemini AI
        prompt = (
            f"Bạn là một người bạn và trợ lý ảo thông minh. THÔNG TIN QUAN TRỌNG:\n"
            f"- Thời gian hiện tại: {now_str}\n"
            f"- Vị trí: Biên Hòa, Đồng Nai.\n"
            f"- Nhiệt độ phòng hiện tại: {temp_str}°C, Độ ẩm: {hum_str}%.\n"
            f"Hãy dùng những thông tin này để trả lời tự nhiên nếu được hỏi.\n"
            f"Dưới đây là lịch sử trò chuyện:\n{chat_history}\n"
            "Hãy nghe đoạn âm thanh tiếp theo của tôi. BẮT BUỘC chỉ trả về đúng 1 chuỗi theo định dạng: "
            "Câu tôi nói|Câu bạn trả lời\n"
            "Quy tắc QUAN TRỌNG:\n"
            "1. Nếu tôi đang kể chuyện hoặc cần tư vấn, hãy chủ động HỎI LẠI để duy trì cuộc trò chuyện.\n"
            "2. Trả lời ngắn gọn nhưng ĐẦY ĐỦ THÔNG TIN, tối đa 3-4 câu (khoảng 40-60 chữ). Cung cấp kiến thức cụ thể.\n"
            "Ví dụ: Thời tiết hôm nay thế nào|Hôm nay trời nắng đẹp, bạn định đi chơi à?\n"
            "LƯU Ý: Phải có dấu gạch đứng '|' ngăn cách."
        )

        print("[*] Đang gửi lên Gemini AI...")
        response = model.generate_content([
            prompt,
            {"mime_type": "audio/wav", "data": wav_bytes}
        ])
        
        reply_text = response.text.strip()
        print(f"[*] Gemini phản hồi: {reply_text}")
        
        # Phân tách chuỗi
        parts = reply_text.split('|')
        if len(parts) >= 2:
            user_text_raw = parts[0].strip()
            tts_text = parts[1].strip()
        else:
            user_text_raw = "Loi"
            tts_text = reply_text
            
        import unicodedata
        def remove_accents(input_str):
            nfkd = unicodedata.normalize('NFKD', input_str)
            res = "".join([c for c in nfkd if not unicodedata.combining(c)])
            return res.replace('đ', 'd').replace('Đ', 'D')
            
        screen_text = remove_accents(tts_text)
        user_text = remove_accents(user_text_raw)
            
        # Cập nhật lịch sử trò chuyện
        chat_history += f"Người dùng: {user_text}\nAI: {tts_text}\n"
        # Chỉ giữ lại khoảng 1000 ký tự cuối để tránh nhồi quá nhiều vào Prompt
        if len(chat_history) > 1000:
            chat_history = chat_history[-1000:]
            
        # 3. Tạo file âm thanh MP3 bằng Google TTS
        print("[*] Đang tạo giọng nói MP3 (Google TTS)...")
        tts = gTTS(text=tts_text, lang='vi', slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_bytes = mp3_fp.getvalue()
        
        # 4. Đóng gói trả về cho ESP32
        # Mã hóa Base64 cho Header để đảm bảo an toàn mạng
        user_b64 = base64.b64encode(user_text.encode('utf-8')).decode('utf-8')
        screen_b64 = base64.b64encode(screen_text.encode('utf-8')).decode('utf-8')
        
        headers = {
            "X-User-Text": user_b64,
            "X-Screen-Text": screen_b64
        }
        
        print("[*] Gửi trả MP3 về ESP32 thành công!\n")
        return Response(content=mp3_bytes, media_type="audio/mpeg", headers=headers)

    except Exception as e:
        print(f"[!] LỖI SERVER: {e}")
        return Response(status_code=500, content=str(e))

if __name__ == "__main__":
    print("🚀 Bắt đầu khởi động AI Server tại cổng 8000...")
    print("👉 Hướng dẫn: Mở terminal chạy lệnh: python server.py")
    uvicorn.run(app, host="0.0.0.0", port=8000)
