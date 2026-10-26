# -*- coding: utf-8 -*-
"""CAD Copilot: импорт и редактирование DXF R12.

Парсит секцию ENTITIES (LINE, коды 8/10/20/11/21), группирует линии
по слоям и восстанавливает контуры комнат. Работает с выводом
generate_dxf() (и с файлами, сохранёнными ezdxf в R12).

API:
  read_dxf(path)                  -> {"lines": [(layer, x1, y1, x2, y2)],
                                      "rooms": [(layer, x, y, w, h)]}
  shift_room(dxf, layer, dx, dy)  -> dxf (сдвиг всех линий слоя)
  remove_room(dxf, layer)         -> dxf
  save_dxf(dxf, path)             -> path (чистый R12, ASCII)
"""
from pathlib import Path
from collections import defaultdict

_CODE = {"8": "layer", "10": "x1", "20": "y1", "11": "x2", "21": "y2"}


def _pairs(text: str):
    vals = [ln.strip() for ln in text.splitlines()]
    for i in range(0, len(vals) - 1, 2):
        yield vals[i], vals[i + 1]


def _read_entities(text: str) -> list:
    ents, cur, inside = [], None, False
    for code, val in _pairs(text):
        if code == "0":
            if cur:
                ents.append(cur)
            cur, inside = ({"kind": val}, val != "EOF") if val != "ENDSEC" else (None, inside)
        elif code == "ENDSEC":
            inside = False
        elif inside and cur and code in _CODE:
            cur[_CODE[code]] = val
    if cur:
        ents.append(cur)
    return ents


def read_dxf(path: str) -> dict:
    raw = Path(path).read_bytes().decode("utf-8", "replace")
    ents = [e for e in _read_entities(raw) if e.get("kind") == "LINE"]
    lines = [(e.get("layer", "0").upper(), float(e["x1"]), float(e["y1"]),
              float(e["x2"]), float(e["y2"])) for e in ents]
    rooms = _rects(lines)
    return {"lines": lines, "rooms": rooms}


def _rects(lines: list) -> list:
    """bbox по каждому слою -> [(layer, x, y, w, h)]."""
    by = defaultdict(list)
    for layer, x1, y1, x2, y2 in lines:
        by[layer].append((x1, y1, x2, y2))
    out = []
    for layer, pts in by.items():
        xs = [p[0] for p in pts] + [p[2] for p in pts]
        ys = [p[1] for p in pts] + [p[3] for p in pts]
        out.append((layer, min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))
    return out


def shift_room(dxf: dict, layer: str, dx: float, dy: float) -> dict:
    L = layer.upper()
    dxf["lines"] = [(*l[:1], l[1] + dx, l[2] + dy, l[3] + dx, l[4] + dy)
                    if l[0] == L else l for l in dxf["lines"]]
    dxf["rooms"] = _rects(dxf["lines"])
    return dxf


def remove_room(dxf: dict, layer: str) -> dict:
    L = layer.upper()
    dxf["lines"] = [l for l in dxf["lines"] if l[0] != L]
    dxf["rooms"] = _rects(dxf["lines"])
    return dxf


def save_dxf(dxf: dict, path: str) -> str:
    out = ["0", "SECTION", "2", "ENTITIES"]
    for layer, x1, y1, x2, y2 in dxf["lines"]:
        out += ["0", "LINE", "8", layer,
                "10", f"{x1:g}", "20", f"{y1:g}", "11", f"{x2:g}", "21", f"{y2:g}"]
    out += ["0", "ENDSEC", "0", "EOF"]
    Path(path).write_text("\n".join(out), encoding="ascii")
    return path
