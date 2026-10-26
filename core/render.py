# -*- coding: utf-8 -*-
"""CAD Copilot: рендеры архитектурной модели в DXF R12 и SVG.

Оба рендера потребляют один и тот же список примитивов из core/model.build_plan(),
так что чертёж в AutoCAD и превью не расходятся ни линией.
"""
from pathlib import Path

# DXF R12: номер цвета AutoCAD по слою
DXF_COLOR = {"Steny": 7, "Peregorodki": 8, "Okna": 4, "Dveri": 2,
             "Razmery": 3, "Explication": 7, "Titles": 7}

SVG_CSS = {  # слой: (цвет, толщина px, размер шрифта множитель)
    "Steny":        ("#1f2937", 2.6),
    "Peregorodki":  ("#374151", 1.8),
    "Okna":         ("#0284c7", 1.6),
    "Dveri":        ("#b45309", 1.4),
    "Razmery":      ("#15803d", 0.9),
    "Explication":  ("#334155", 1.0),
    "Titles":       ("#111827", 1.6),
}

ANG = __import__("math")


def render_dxf(plan: dict, path: str) -> str:
    """Примитивы -> DXF R12 (ASCII, cp1251 для кириллицы в TEXT)."""
    x0, y0 = plan["canvas"][0], plan["canvas"][1]
    x1, y1 = plan["canvas"][2], plan["canvas"][3]
    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009",
         "9", "$EXTMIN", "10", _f(x0), "20", _f(y0), "30", "0.0",
         "9", "$EXTMAX", "10", _f(x1), "20", _f(y1), "30", "0.0", "0", "ENDSEC"]
    L += ["0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER",
          "70", str(len(DXF_COLOR))]
    for lay, col in DXF_COLOR.items():
        L += ["0", "LAYER", "2", lay, "70", "0", "62", str(col), "6", "CONTINUOUS"]
    L += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for pr in plan["prims"]:
        kind = pr[0]
        if kind == "line":
            _, lay, x1_, y1_, x2_, y2_ = pr
            L += ["0", "LINE", "8", lay, "10", _f(x1_), "20", _f(y1_),
                  "11", _f(x2_), "21", _f(y2_)]
        elif kind == "arc":
            _, lay, cx, cy, r, s, e = pr
            L += ["0", "ARC", "8", lay, "10", _f(cx), "20", _f(cy),
                  "40", _f(r), "50", _f(s), "51", _f(e)]
        elif kind == "text":
            _, lay, x, y, h, s, align = pr
            L += ["0", "TEXT", "8", lay, "10", _f(x), "20", _f(y),
                  "40", _f(h), "1", s]
            if align == "c":
                L += ["72", "1", "11", _f(x), "21", _f(y)]
    L += ["0", "ENDSEC", "0", "EOF"]
    Path(path).write_text("\n".join(L), encoding="cp1251")
    return path


def _f(v) -> str:
    v = float(v) + 0.0
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0.0"


def render_svg(plan: dict, path: str, scale: float = 48.0) -> str:
    """Примитивы -> SVG (Y переворачивается: в SVG рост вниз)."""
    cx0, cy0, cx1, cy1 = plan["canvas"]
    W, H = (cx1 - cx0) * scale, (cy1 - cy0) * scale
    fy = lambda y: (cy1 - y) * scale  # мир -> SVG
    fx = lambda x: (x - cx0) * scale

    def txt_h(h):
        return h * scale

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
             f'width="{W:.0f}" height="{H:.0f}">',
             f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']
    for pr in plan["prims"]:
        kind, lay = pr[0], pr[1]
        col, lw = SVG_CSS.get(lay, ("#111", 1.0))
        if kind == "line":
            _, _, xa, ya, xb, yb = pr
            parts.append(f'<line x1="{fx(xa):.1f}" y1="{fy(ya):.1f}" '
                         f'x2="{fx(xb):.1f}" y2="{fy(yb):.1f}" stroke="{col}" '
                         f'stroke-width="{lw}"/>')
        elif kind == "arc":
            _, _, cx, cy, r, s, e = pr
            s, e = ANG.radians(s), ANG.radians(e)
            pts = []
            steps = 24
            for i in range(steps + 1):
                a = s + (e - s) * i / steps
                pts.append((cx + r * ANG.cos(a), cy + r * ANG.sin(a)))
            d = "M " + " L ".join(f"{fx(px):.1f},{fy(py):.1f}" for px, py in pts)
            parts.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{lw}"/>')
        elif kind == "text":
            _, _, x, y, h, s, align = pr
            anchor = "middle" if align == "c" else "start"
            parts.append(f'<text x="{fx(x):.1f}" y="{fy(y):.1f}" font-family="Segoe UI" '
                         f'font-size="{txt_h(h):.1f}" fill="{col}" text-anchor="{anchor}">{s}</text>')
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")
    return path
