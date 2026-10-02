import os
import io
import base64
from fastapi import FastAPI, Request, Response
from groq import Groq
from gtts import gTTS
import uvicorn
import datetime
import unicodedata

app = FastAPI()

# --- CẤU HÌNH GROQ API KEY ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("[!] CẢNH BÁO: Chưa cấu hình GROQ_API_KEY trong Environment Variables!")

# Khởi tạo client Groq
try:
    client = Groq(api_key=GROQ_API_KEY)
    print("[*] Groq API khởi tạo thành công!")
except Exception as e:
    print(f"[!] Lỗi khởi tạo Groq: {e}")

# Biến lưu trữ lịch sử trò chuyện tạm thời
chat_history = []

def remove_accents(input_str):
    nfkd = unicodedata.normalize('NFKD', input_str)
    res = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return res.replace('đ', 'd').replace('Đ', 'D')

@app.post("/chat")
async def chat(request: Request):
    global chat_history
    
    # 1. Nhận file WAV thô từ ESP32
    wav_bytes = await request.body()
    print(f"[*] Đã nhận {len(wav_bytes)} bytes âm thanh từ ESP32.")
    
    if len(wav_bytes) == 0:
        return Response(status_code=400, content="Không có dữ liệu âm thanh")

    try:
        # Lấy ngày giờ và môi trường
        days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        now_dt = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        now_str = f"{now_dt.strftime('%H:%M:%S')} {days[now_dt.weekday()]} ngày {now_dt.strftime('%d/%m/%Y')}"
        
        temp_str = request.headers.get("X-Temperature", "Không xác định")
        hum_str = request.headers.get("X-Humidity", "Không xác định")
        
        # 2. CHUYỂN GIỌNG NÓI THÀNH VĂN BẢN (Whisper)
        print("[*] Đang nhận diện giọng nói bằng Whisper...")
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes, "audio/wav"),
            model="whisper-large-v3",
            language="vi",
        )
        user_text_raw = transcription.text.strip()
        print(f"[*] Người dùng nói: {user_text_raw}")
        
        if not user_text_raw:
            user_text_raw = "Xin chào"
            
        # 3. GỬI LÊN LLAMA 3 (Xử lý AI)
        system_prompt = (
            f"Bạn là một trợ lý ảo quản gia thông minh và vui tính.\n"
            f"THÔNG TIN QUAN TRỌNG:\n"
            f"- Thời gian hiện tại: {now_str}\n"
            f"- Vị trí: Biên Hòa, Đồng Nai.\n"
            f"- Nhiệt độ phòng: {temp_str}°C, Độ ẩm: {hum_str}%.\n"
            f"Quy tắc:\n"
            f"1. Trả lời ngắn gọn, thân thiện, tự nhiên như người Việt, tối đa 3-4 câu.\n"
            f"2. Nếu người dùng hỏi thời tiết hay giờ giấc, hãy dựa vào dữ liệu trên để trả lời.\n"
            f"3. TUYỆT ĐỐI KHÔNG dùng các ký tự markdown như *, #, \n"
        )
        
        # Build messages for Llama 3
        messages = [{"role": "system", "content": system_prompt}]
        for chat in chat_history:
            messages.append({"role": chat["role"], "content": chat["content"]})
        messages.append({"role": "user", "content": user_text_raw})
        
        print("[*] Đang gửi lên Groq Llama 3...")
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        tts_text = completion.choices[0].message.content.strip()
        print(f"[*] Llama 3 phản hồi: {tts_text}")
        
        # Lưu vào lịch sử
        chat_history.append({"role": "user", "content": user_text_raw})
        chat_history.append({"role": "assistant", "content": tts_text})
        if len(chat_history) > 10: # Giữ 5 vòng lặp gần nhất
            chat_history = chat_history[-10:]
            
        screen_text = remove_accents(tts_text)
        user_text = remove_accents(user_text_raw)
            
        # 4. Tạo file âm thanh MP3 bằng Google TTS
        print("[*] Đang tạo giọng nói MP3 (Google TTS)...")
        tts = gTTS(text=tts_text, lang='vi', slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_bytes = mp3_fp.getvalue()
        
        # 5. Đóng gói trả về cho ESP32
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
    print("🚀 Bắt đầu khởi động Groq AI Server tại cổng 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
