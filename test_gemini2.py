import urllib.request
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
                    "text": "Bạn là trợ lý ảo AI. Trả lời câu hỏi sau bằng Tiếng Việt. Trả về JSON với 'tts' (có dấu) và 'screen' (không dấu). Câu hỏi: Thoi tiet the nao?"
                }
            ]
        }
    ]
}

req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print("Status Code:", response.status)
        print("Response:", response.read().decode('utf-8'))
except Exception as e:
    print(e)
