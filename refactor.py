import re

with open('src/main.cpp', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add drawEQBars(int energy) function above drawListeningUI
eq_func = """
// --- Hiệu ứng Music Visualizer (Fake FFT EQ Bars) ---
void drawEQBars(int energy) {
    static const uint16_t EQ_COLORS[24] = {
      0xF800, 0xF800, 0xF804, 0xF808, 
      0xF80C, 0xF810, 0xF814, 0xF818, 
      0xF81C, 0xF81F, 0xD81F, 0xB81F, 
      0x981F, 0x781F, 0x581F, 0x381F, 
      0x181F, 0x001F, 0x01FF, 0x03FF, 
      0x05FF, 0x07FF, 0x07FF, 0x07FF  
    };
    
    static float phase = 0;
    phase += 0.4;
    
    static int old_bar_height[24] = {0};
    
    int max_amp = map(energy, 0, 5000, 5, 80);
    if (max_amp > 80) max_amp = 80;
    if (max_amp < 5) max_amp = 5;

    for (int i = 0; i < 24; i++) {
        float wave = abs(sin(i * 0.5 + phase) * cos(i * 0.3 - phase * 0.7));
        float noise = (float)random(60, 100) / 100.0;
        float center_boost = 1.0 - abs(i - 11.5) / 12.0; 
        
        int target_h = 5 + max_amp * wave * noise * (0.5 + 0.8 * center_boost);
        if (target_h > 80) target_h = 80;
        
        int h = old_bar_height[i];
        
        if (target_h > h) {
            h = target_h;
        } else {
            h -= 4;
            if (h < 5) h = 5;
        }
        
        int x = i * 10 + 1; 
        int old_h = old_bar_height[i];
        
        if (h < old_h) {
            tft.fillRect(x, 230 - old_h, 8, old_h - h, COLOR_BG);
        } else if (h > old_h) {
            tft.fillRect(x, 230 - h, 8, h - old_h, EQ_COLORS[i]);
        }
        
        if (old_h == 0) {
           tft.fillRect(x, 230 - 5, 8, 5, EQ_COLORS[i]); 
        }
        
        old_bar_height[i] = h;
    }
}
"""
content = content.replace('void drawListeningUI(const char* lastAiText) {', eq_func + '\nvoid drawListeningUI(const char* lastAiText, const char* topStatus) {')

content = content.replace('printText("+ Live", 95, 30, COLOR_WHITE, &FreeSans9pt7b);', 'printText(topStatus, 80, 30, COLOR_WHITE, &FreeSans9pt7b);')
content = content.replace('drawListeningUI(lastAiTextGlobal.c_str());', 'drawListeningUI(lastAiTextGlobal.c_str(), "+ Live");')

# Replace inline EQ
inline_eq = re.search(r'// --- Hiệu ứng Music Visualizer \(Fake FFT EQ Bars\) ---.*?old_bar_height\[i\] = h;\n        }', content, re.DOTALL)
if inline_eq:
    content = content.replace(inline_eq.group(0), 'drawEQBars(energy);')

# Replace sending
content = content.replace('drawChatUI("...", "Dang gui am thanh len Server...");', 'tft.fillRect(0, 0, 240, 40, COLOR_BG); printText("Thinking...", 75, 30, COLOR_WHITE, &FreeSans9pt7b); for(int i=0; i<15; i++) { drawEQBars(0); delay(20); }')

# Replace receiving
content = content.replace('drawChatUI(userText.c_str(), screenText.c_str());', 'lastAiTextGlobal = screenText.c_str(); drawListeningUI(lastAiTextGlobal.c_str(), "+ Live");')

# Replace Error UI
content = content.replace('drawChatUI("Loi ket noi Server", String(httpCode).c_str());', 'tft.fillRect(0, 0, 240, 40, COLOR_BG); printText("Connection Error!", 50, 30, COLOR_WHITE, &FreeSans9pt7b);')
content = content.replace('drawChatUI("Loi", "Khong du RAM!");', 'printText("RAM Error", 70, 30, COLOR_WHITE, &FreeSans9pt7b);')

# Remove void drawChatUI completely
chat_ui = re.search(r'void drawChatUI\(const char\* userText, const char\* aiText\).*?^\}', content, re.DOTALL | re.MULTILINE)
if chat_ui:
    content = content.replace(chat_ui.group(0), "")

# Replace mp3 loop
mp3_loop = """                  if (mp3->begin(ramFile, out)) {
                      long last_eq = 0;
                      while (mp3->isRunning()) {
                          if (!mp3->loop()) {
                              mp3->stop();
                              break; 
                          }
                          if (millis() - last_eq > 50) {
                              last_eq = millis();
                              drawEQBars(random(1000, 4500));
                          }
                          delay(1);
                      }"""
content = re.sub(r'if \(mp3->begin\(ramFile, out\)\) \{.*?while \(mp3->isRunning\(\)\) \{.*?if \(\!mp3->loop\(\)\) \{.*?mp3->stop\(\);.*?break; \n                          \}.*?delay\(1\);.*?\}', mp3_loop, content, flags=re.DOTALL)

with open('src/main.cpp', 'w', encoding='utf-8') as f:
    f.write(content)
