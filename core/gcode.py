# -*- coding: utf-8 -*-
"""CAD Copilot: G-code экспорт для ЧПУ (лазер/фрезер/плоттер).

Та же спецификация -> тот же layout() -> G-code. Единицы — миллиметры (G21),
абсолютные координаты (G90), безопасный подъём между контурами.
"""
from pathlib import Path
from core.autocad_ai import layout

TR = dict(zip("абвгдежзийклмнопрстуфхцчшщъыьэюя",
              "abvgdezzijklmnoprstufhccss'y'eua"))


def tr(s: str) -> str:
    return "".join(TR.get(c, c) for c in s.lower())


def generate_gcode(spec: dict, path: str, scale: float = 1000.0,
                   feed: int = 1200, travel: int = 3000,
                   z_safe: float = 5.0, z_cut: float = -1.0) -> str:
    """Spec -> G-code. 1 м чертежа = `scale` мм; вырезаем контуры комнат
    (многоугольники) и помечаем их комментариями дляpost-процессора."""
    if scale <= 0:
        raise ValueError("scale must be > 0")
    lines = [
        "G21 ; millimeters", "G90 ; absolute",
        f"G0 Z{z_safe:.1f} ; lift",
        f"G0 F{travel} ; travel feed down (sets modal F for G0)",
    ]
    for name, x, y, w, h in layout(spec):
        room = tr(name) if tr(name) else "ROOM"
        lines.append(f"; ROOM {room} {w}x{h}")
        px = [ (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y) ]
        lines.append(f"G0 X{px[0][0]*scale:.1f} Y{px[0][1]*scale:.1f} F{travel}")
        lines.append(f"G1 Z{z_cut:.1f} F{feed // 2} ; plunge")
        for vx, vy in px[1:]:
            lines.append(f"G1 X{vx*scale:.1f} Y{vy*scale:.1f} F{feed}")
        lines.append(f"G0 Z{z_safe:.1f} ; lift")
    lines.append("G0 X0 Y0")
    Path(path).write_text("\n".join(lines) + "\n", encoding="ascii")
    return path
