import requests
from io import BytesIO
from PIL import Image

# Generate a Huawei-style logo
img = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
from PIL import ImageDraw
import math

draw = ImageDraw.Draw(img)
center_x, center_y = 60, 90
petals = 8
for i in range(petals):
    angle = math.radians(180 + 20 + i * 20)  # Spread from 200 to 340 degrees
    length = 50 if (i > 1 and i < 6) else 40
    if i == 3 or i == 4: length = 60
    
    end_x = center_x + math.cos(angle) * length
    end_y = center_y + math.sin(angle) * length
    draw.line([(center_x, center_y), (end_x, end_y)], fill=(255, 0, 0, 255), width=8, joint="curve")

base_img = img

# Resize the base image to 120x120
base_img = img.resize((120, 120), Image.Resampling.LANCZOS)

# Create 6 frames for a pulsing animation
scales = [1.0, 0.9, 0.8, 0.7, 0.8, 0.9]
frames = []

for scale in scales:
    size = int(120 * scale)
    scaled = base_img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Create a 120x120 transparent canvas
    canvas = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    # Paste the scaled image in the center
    offset = ((120 - size) // 2, (120 - size) // 2)
    canvas.paste(scaled, offset, scaled)
    
    # Convert RGBA to RGB565 on a black background
    bg = Image.new("RGB", (120, 120), (8, 37, 37)) # COLOR_BG in RGB approx (8, 37, 37) is close to 0x0825 (r:8, g:37, b:37)? Actually 0x0825 -> R: 00001 (8), G: 000001 (4), B: 00101 (41). Let's just use (0,0,0) or (8,37,41). Let's use exact match for 0x0825: R=8, G=36, B=41.
    bg.paste(canvas, mask=canvas.split()[3]) # Use alpha channel as mask
    
    pixels = bg.load()
    rgb565_data = []
    for y in range(120):
        for x in range(120):
            r, g, b = pixels[x, y]
            # Convert to RGB565
            r5 = (r >> 3) & 0x1F
            g6 = (g >> 2) & 0x3F
            b5 = (b >> 3) & 0x1F
            rgb565 = (r5 << 11) | (g6 << 5) | b5
            rgb565_data.append(rgb565)
    frames.append(rgb565_data)

# Write to C header file
with open("src/huawei_logo.h", "w") as f:
    f.write("#pragma once\n\n")
    f.write("#include <Arduino.h>\n\n")
    f.write(f"const uint16_t huawei_logo_frames[6][14400] PROGMEM = {{\n")
    
    for i, frame in enumerate(frames):
        f.write("  {\n    ")
        for j, pixel in enumerate(frame):
            f.write(f"0x{pixel:04X}, ")
            if (j + 1) % 12 == 0:
                f.write("\n    ")
        f.write("\n  }")
        if i < 5:
            f.write(",\n")
        else:
            f.write("\n")
    
    f.write("};\n")

print("Generated src/huawei_logo.h with 6 animated frames!")
