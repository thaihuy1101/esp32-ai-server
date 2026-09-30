$body = @{
    generationConfig = @{
        responseMimeType = "application/json"
    }
    contents = @(
        @{
            parts = @(
                @{
                    text = "Bạn là trợ lý ảo ngắn gọn. Hãy trả lời câu hỏi sau. BẮT BUỘC trả về JSON gồm 2 trường: tts (câu trả lời tiếng Việt CÓ DẤU) và screen (câu trả lời tiếng Việt KHÔNG DẤU, không chứa ký tự đặc biệt). Câu hỏi: Thoi tiet hom nay the nao?"
                }
            )
        }
    )
}
$json = $body | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=AQ.Ab8RN6Iw18kqxhxLbPtVeadi9YhsD6QEyTM1S3YcAds1eEC0oA" -Method Post -Body $json -ContentType "application/json"
