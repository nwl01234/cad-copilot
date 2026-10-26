# -*- coding: utf-8 -*-
"""CAD Copilot: текст -> спецификация -> DXF + SVG.

Офлайн-ядро: работает без GPU и без интернета.
"""
import re
from pathlib import Path

NUM = r"(\d+(?:[.,]\d+)?)"
ROOM_RE = re.compile(r"(комната|кухня|коридор|ванная|санузел|зал|офис)\D*" + NUM + r"\s*[x×х]\s*" + NUM, re.I)
DOOR_RE = re.compile(r"двер(?:ь|и|ную)", re.I)
WIN_RE = re.compile(r"окн(?:о|а|ом)", re.I)

WIN_NUM = re.compile(r"(\d+)\s*окн", re.I)
DOOR_NUM = re.compile(r"(\d+)\s*двер", re.I)

def _count(num_re, word_re, text):
    nums = [int(n) for n in num_re.findall(text)]
    return sum(nums) if nums else len(word_re.findall(text))

def parse_request(text: str) -> dict:
    """Текст -> spec: rooms [(name, w, h)], doors, windows."""
    rooms = [(m.group(1).lower(), float(m.group(2).replace(",", ".")),
              float(m.group(3).replace(",", "."))) for m in ROOM_RE.finditer(text)]
    if not rooms:
        rooms = [("комната", 4.0, 5.0)]
    return {"rooms": rooms, "doors": _count(DOOR_NUM, DOOR_RE, text),
            "windows": _count(WIN_NUM, WIN_RE, text)}

def layout(spec: dict) -> list:
    """Раскладка комнат на плане: [(name, x, y, w, h)]."""
    out, x, y = [], 0.0, 0.0
    for name, w, h in spec["rooms"]:
        if x + w > 12.0:              # строка заполнена — перенос
            x, y = 0.0, max(r[2] + r[4] for r in out) + 0.2
        out.append((name, x, y, w, h))
        x += w + 0.2
    return out

def generate_dxf(spec: dict, path: str) -> str:
    """Пишет DXF R12 (работает без ezdxf; с ezdxf — форматированный вывод)."""
    try:
        import ezdxf
        doc = ezdxf.new("R2000")
        msp = doc.modelspace()
        TR = dict(zip("абвгдежзийклмнопрстуфхцчшщъыьэюя", "abvgdezzijklmnoprstufhccss'y'eua"))
        tr = lambda s: "".join(TR.get(c, c) for c in s.lower()).upper() or "ROOM"
        for name, x, y, w, h in layout(spec):
            L = tr(name)
            if L not in doc.layers:
                doc.layers.add(L)
            pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
            for i in range(4):
                msp.add_line(pts[i], pts[i + 1], dxfattribs={"layer": L})
            msp.add_text(name, dxfattribs={"height": 0.25, "layer": L}).set_placement((x + 0.3, y + h - 0.4))
        for _ in range(spec["doors"]):
            msp.add_line((0, 0), (0, 0))
        doc.saveas(path)
    except ImportError:
        TR = dict(zip("абвгдежзийклмнопрстуфхцчшщъыьэюя", "abvgdezzijklmnoprstufhccss'y'eua"))
        tr = lambda s: "".join(TR.get(c, c) for c in s.lower()).upper() or "ROOM"
        lines = ["0", "SECTION", "2", "ENTITIES"]
        for name, x, y, w, h in layout(spec):
            L = tr(name)
            pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            for i in range(4):
                a, b = pts[i], pts[(i + 1) % 4]
                lines += ["0", "LINE", "8", L, "10", f"{a[0]}", "20", f"{a[1]}", "11", f"{b[0]}", "21", f"{b[1]}"]
            lines += ["0", "TEXT", "8", L, "10", f"{x + 0.3}", "20", f"{y + h - 0.4}", "40", "0.25", "1", L]
        lines += ["0", "ENDSEC", "0", "EOF"]
        Path(path).write_text("\n".join(lines), encoding="ascii")
    return path

def render_svg(spec: dict, path: str) -> str:
    """SVG-превью плана (для отчётов и фронтенда)."""
    W, S = 640, 28
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{S * 7}">']
    parts.append(f'<rect width="{W}" height="{S * 7}" fill="#f8fafc"/>')
    for name, x, y, w, h in layout(spec):
        px, py, pw, ph = S + x * S, S + y * S, w * S, h * S
        parts.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>')
        parts.append(f'<text x="{px + 8}" y="{py + 20}" font-family="Segoe UI" font-size="13" fill="#1e3a8a">{name} {w}x{h}</text>')
    for _ in range(spec["doors"]):
        parts.append(f'<path d="M {S} {S} a 26 26 0 0 1 26 26" stroke="#f59e0b" fill="none" stroke-width="3"/>')
    for _ in range(spec["windows"]):
        parts.append(f'<line x1="{W - 60}" y1="{S + 4}" x2="{W - 60}" y2="{S + 40}" stroke="#38bdf8" stroke-width="6"/>')
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")
    return path
