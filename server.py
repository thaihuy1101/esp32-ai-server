import os
import uuid
import asyncio
import re
import requests
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, Response
import edge_tts
from groq import AsyncGroq

app = FastAPI()

# Môi trường Groq API
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = AsyncGroq(api_key=GROQ_API_KEY)

# Dict lưu trữ hàng đợi âm thanh cho mỗi session
audio_queues = {}

def get_weather_info():
    try:
        # Lấy thời tiết Bắc Tân Uyên, Bình Dương
        lat, lon = 11.0827, 106.8457
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        headers = {'User-Agent': 'ESP32-AI-Assistant/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            temp = data['current_weather']['temperature']
            return f"Thời tiết thực tế ngoài trời tại Bắc Tân Uyên hiện tại là {temp} độ C."
    except Exception as e:
        print("Lỗi thời tiết:", e)
    return "Không thể lấy thông tin thời tiết lúc này."

async def process_llm_and_tts(session_id: str, user_text: str):
    buffer = ""
    split_chars = {'.', '!', '?', '\n', ';'}
    
    try:
        weather_context = get_weather_info()
        sys_prompt = (
            f"Bạn là trợ lý ảo Qwen AI. Hãy trả lời ngắn gọn, tự nhiên, bằng tiếng Việt. "
            f"Thông tin thời tiết: {weather_context}"
        )
        
        response = await client.chat.completions.create(
            model="qwen-2.5-32b",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text}
            ],
            stream=True,
            temperature=0.7,
            max_tokens=200
        )
        
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                buffer += delta
                
                # Split buffer by punctuation marks to stream out complete sentences
                matches = list(re.finditer(r'([.!?:;\n]+)', buffer))
                if matches:
                    last_match = matches[-1]
                    split_idx = last_match.end()
                    
                    complete_sentences = buffer[:split_idx].strip()
                    buffer = buffer[split_idx:]
                    
                    if complete_sentences:
                        communicate = edge_tts.Communicate(complete_sentences, "vi-VN-HoaiMyNeural")
                        async for tts_chunk in communicate.stream():
                            if tts_chunk["type"] == "audio":
                                await audio_queues[session_id].put(tts_chunk["data"])
                                
        # Flush the remaining buffer if any
        if buffer.strip():
            communicate = edge_tts.Communicate(buffer.strip(), "vi-VN-HoaiMyNeural")
            async for tts_chunk in communicate.stream():
                if tts_chunk["type"] == "audio":
                    await audio_queues[session_id].put(tts_chunk["data"])
                    
    except Exception as e:
        print(f"Lỗi AI/TTS: {e}")
    finally:
        # Bắn tín hiệu kết thúc luồng (EOF)
        if session_id in audio_queues:
            await audio_queues[session_id].put(None)

@app.post("/chat")
async def chat_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # 1. Lưu file WAV tạm thời
    audio_content = await file.read()
    temp_file_path = f"temp_{uuid.uuid4().hex}.wav"
    with open(temp_file_path, "wb") as f:
        f.write(audio_content)
        
    user_text_raw = ""
    try:
        # 2. Gửi cho Whisper giải mã
        with open(temp_file_path, "rb") as f:
            transcription = await client.audio.transcriptions.create(
                file=(temp_file_path, f.read()),
                model="whisper-large-v3",
                prompt="Đây là tiếng Việt.",
                language="vi"
            )
        user_text_raw = transcription.text.strip()
    except Exception as e:
        print("Lỗi Whisper:", e)
        return Response(status_code=500)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # 3. Bộ lọc ảo giác
    text_lower = user_text_raw.lower()
    short_hallucinations = ["xin chào", "cảm ơn", "tạm biệt", "hẹn gặp lại", "chào các bạn"]
    youtube_hallucinations = ["đăng ký kênh", "theo dõi", "subscribe", "subtitles", "la la school", "bỏ lỡ những video"]
    
    is_hallucination = False
    if len(user_text_raw) < 2:
        is_hallucination = True
    elif len(user_text_raw) < 20 and any(h == text_lower.strip() or h in text_lower for h in short_hallucinations):
        is_hallucination = True
    elif any(h in text_lower for h in youtube_hallucinations):
        is_hallucination = True
        
    if is_hallucination:
        print(f"[*] Ảo giác: {user_text_raw}")
        return Response(status_code=204) 
    
    if not user_text_raw:
        return Response(status_code=204)
        
    print(f"[*] User nói: {user_text_raw}")

    # 4. Khởi tạo phiên Streaming
    session_id = str(uuid.uuid4())
    audio_queues[session_id] = asyncio.Queue()
    
    # Kích hoạt tiến trình chạy ngầm: LLM nghĩ -> TTS tạo giọng -> Bơm vào Queue
    background_tasks.add_task(process_llm_and_tts, session_id, user_text_raw)
    
    # 5. Trả về kết quả ngay lập tức cho ESP32
    return JSONResponse(content={
        "session_id": session_id,
        "user_text": user_text_raw
    })

async def audio_streamer(session_id: str):
    queue = audio_queues.get(session_id)
    if not queue:
        return
        
    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk
    finally:
        # Xóa phiên sau khi stream xong
        audio_queues.pop(session_id, None)

@app.get("/stream/{session_id}")
async def stream_endpoint(session_id: str):
    if session_id not in audio_queues:
        return Response(status_code=404)
    # Stream chunk âm thanh trả về ESP32
    return StreamingResponse(audio_streamer(session_id), media_type="audio/mpeg")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "ESP32 Streaming Server is running v2.0"}
