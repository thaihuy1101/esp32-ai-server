import os
import io
import base64
from fastapi import FastAPI, Request, Response
from groq import Groq
import uvicorn
import datetime
import unicodedata
import httpx
import edge_tts

app = FastAPI()

# --- CẤU HÌNH GROQ API KEY ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("[!] CẢNH BÁO: Chưa cấu hình GROQ_API_KEY trong Environment Variables!")

try:
    client = Groq(api_key=GROQ_API_KEY)
    print("[*] Groq API khởi tạo thành công!")
except Exception as e:
    print(f"[!] Lỗi khởi tạo Groq: {e}")

chat_history = []

def remove_accents(input_str):
    nfkd = unicodedata.normalize('NFKD', input_str)
    res = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return res.replace('đ', 'd').replace('Đ', 'D')

def parse_weather(code):
    if code == 0: return "trời trong xanh, không mây"
    if code in [1,2,3]: return "trời có mây"
    if code in [45,48]: return "có sương mù"
    if code in [51,53,55,56,57]: return "có mưa bay, lất phất"
    if code in [61,63,65,66,67,80,81,82]: return "có mưa rào"
    if code in [95,96,99]: return "có giông bão, sấm sét"
    return "thời tiết khá ổn"

async def get_real_weather():
    # Lấy thời tiết thực tế tại Biên Hòa, Đồng Nai
    try:
        async with httpx.AsyncClient() as http_client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = await http_client.get("https://api.open-meteo.com/v1/forecast?latitude=10.9482&longitude=106.8283&current_weather=true", headers=headers, timeout=10.0)
            data = resp.json()
            cw = data["current_weather"]
            temp = cw["temperature"]
            condition = parse_weather(cw["weathercode"])
            return f"{temp}°C, {condition}"
    except Exception as e:
        print(f"[!] Lỗi khi lấy thời tiết ngoài trời: {e}")
        return "không lấy được dữ liệu"

@app.post("/chat")
async def chat(request: Request):
    global chat_history
    
    wav_bytes = await request.body()
    print(f"[*] Đã nhận {len(wav_bytes)} bytes âm thanh từ ESP32.")
    
    if len(wav_bytes) == 0:
        return Response(status_code=400, content="Không có dữ liệu âm thanh")

    try:
        days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        now_dt = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        now_str = f"{now_dt.strftime('%H:%M')} {days[now_dt.weekday()]} ngày {now_dt.strftime('%d/%m/%Y')}"
        
        # Dữ liệu từ ESP32 (Phòng)
        temp_str = request.headers.get("X-Temperature", "Không xác định")
        hum_str = request.headers.get("X-Humidity", "Không xác định")
        
        # Dữ liệu ngoài trời thực tế
        outdoor_weather = await get_real_weather()
        
        print("[*] Đang nhận diện giọng nói bằng Whisper...")
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes, "audio/wav"),
            model="whisper-large-v3",
            language="vi",
        )
        user_text_raw = transcription.text.strip()
        print(f"[*] Người dùng nói: {user_text_raw}")
        
        # Lọc các trường hợp im lặng bị Whisper ảo giác
        text_lower = user_text_raw.lower()
        hallucinations = [
            "xin chào", "cảm ơn", "tạm biệt", "hẹn gặp lại", 
            "đăng ký kênh", "theo dõi", "subscribe", "subtitles", "chào các bạn"
        ]
        
        # Nếu chuỗi quá ngắn hoặc nằm trong danh sách ảo giác phổ biến của Whisper
        if len(user_text_raw) < 2 or any(h == text_lower.strip() or h in text_lower for h in hallucinations):
            if len(user_text_raw) < 15: # Tránh lọc nhầm câu nói thật có chữ "xin chào" dài
                print("[*] Bỏ qua vì phát hiện ảo giác âm thanh (im lặng).")
                return Response(status_code=204) # 204 No Content
        
        if not user_text_raw:
            return Response(status_code=204)
            
        system_prompt = (
            f"Bạn là trợ lý ảo AI thông minh, vui tính và đáng yêu.\n"
            f"THÔNG TIN QUAN TRỌNG ĐỂ TRẢ LỜI:\n"
            f"- Thời gian hiện tại: {now_str}\n"
            f"- Vị trí của người dùng: Biên Hòa, Đồng Nai.\n"
            f"- Nhiệt độ TRONG PHÒNG hiện tại: {temp_str}°C, Độ ẩm: {hum_str}%.\n"
            f"- Thời tiết NGOÀI TRỜI thực tế: {outdoor_weather}.\n"
            f"Quy tắc:\n"
            f"1. Trả lời ngắn gọn, tự nhiên, giống người thật, tối đa 3-4 câu.\n"
            f"2. KHÔNG dùng các ký tự đặc biệt như *, #. KHÔNG thêm các từ như 'vâng', 'dạ' quá nhiều gây nhàm chán.\n"
            f"3. Nếu hỏi về thời tiết ngoài trời, hãy dùng dữ liệu 'Thời tiết NGOÀI TRỜI thực tế' để trả lời.\n"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for chat_msg in chat_history:
            messages.append({"role": chat_msg["role"], "content": chat_msg["content"]})
        messages.append({"role": "user", "content": user_text_raw})
        
        print("[*] Đang gửi lên Groq Qwen...")
        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        tts_text = completion.choices[0].message.content.strip()
        print(f"[*] Qwen phản hồi: {tts_text}")
        
        chat_history.append({"role": "user", "content": user_text_raw})
        chat_history.append({"role": "assistant", "content": tts_text})
        if len(chat_history) > 10: 
            chat_history = chat_history[-10:]
            
        screen_text = remove_accents(tts_text)
        user_text = remove_accents(user_text_raw)
            
        print("[*] Đang tạo giọng nói MP3 (Microsoft Edge TTS - Giọng Hoài My)...")
        # Sử dụng giọng Hoài My (Nữ, Miền Nam, Nghe rất tự nhiên và nhanh)
        communicate = edge_tts.Communicate(tts_text, "vi-VN-HoaiMyNeural")
        
        mp3_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_bytes += chunk["data"]
        
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
    print("🚀 Bắt đầu khởi động AI Server (Groq + Edge TTS) tại cổng 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
