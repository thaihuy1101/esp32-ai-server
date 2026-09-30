import requests
import json

api_key = "AQ.Ab8RN6Iw18kqxhxLbPtVeadi9YhsD6QEyTM1S3YcAds1eEC0oA"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

payload = {
    "generationConfig": {
        "responseMimeType": "application/json"
    },
    "contents": [
        {
            "parts": [
                {
                    "text": "Bạn là trợ lý ảo ngắn gọn. Hãy trả lời câu hỏi sau. BẮT BUỘC trả về JSON gồm 2 trường: 'tts' (câu trả lời tiếng Việt CÓ DẤU) và 'screen' (câu trả lời tiếng Việt KHÔNG DẤU, không chứa ký tự đặc biệt). Câu hỏi: Thoi tiet hom nay the nao?"
                }
            ]
        }
    ]
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
print("Status Code:", response.status_code)
print("Response:", response.text)
