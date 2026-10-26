# -*- coding: utf-8 -*-
"""GIF-демка: запрос -> план, кадры строятся из реального layout()."""
from PIL import Image, ImageDraw, ImageFont
import sys; sys.path.insert(0, ".")
from core.autocad_ai import parse_request, layout
F = {13: ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 13),
     11: ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 11)}

spec = parse_request("комната 4x5, комната 3x4, кухня 3x3, ванная 2x3, дверь, 2 окна")
boxes = layout(spec)
W, S, ROWS = 660, 42, 7

def draw(step, windows=False, door=False):
    img = Image.new("RGB", (W, S * ROWS), "#f8fafc")
    d = ImageDraw.Draw(img)
    for name, x, y, w, h in boxes[:step]:
        px, py, pw, ph = S + x*S, S + y*S, w*S, h*S
        d.rectangle([px, py, px+pw, py+ph], fill="#dbeafe", outline="#2563eb", width=3)
        d.text((px+8, py+10), f"{name} {w:g}x{h:g}".replace(".0",""), fill="#1e3a8a", font=F[13])
    if door and step >= len(boxes):
        d.arc([S-4, S-4, S+50, S+50], 270, 360, fill="#f59e0b", width=4)
    if windows and step >= len(boxes):
        for i in range(2):
            wx = S + (i + 1) * (W - 2*S) // 3
            d.rectangle([wx-4, S+4, wx+4, S+64], fill="#38bdf8")
    d.text((S, 8), 'запрос: "комната 4x5, комната 3x4, кухня 3x3, ванная 2x3, дверь, 2 окна"',
           fill="#334155", font=F[13])
    return img

frames = []
for i in range(1, len(boxes) + 1):
    frames.append((draw(i), 700))
frames += [(draw(len(boxes), door=True, windows=True), 700), (draw(len(boxes), door=True, windows=True), 2600)]
frames[0][0].save("skrin/demo.gif", save_all=True, append_images=[f for f, _ in frames[1:]],
                  duration=[dur for _, dur in frames] + [500], loop=0)
print("frames:", len(frames))
