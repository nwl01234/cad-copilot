# -*- coding: utf-8 -*-
"""Демо: текстовый запрос -> чертёж. Запуск: python demo.py"""
from core.autocad_ai import generate_dxf, parse_request, render_svg

TEXT = "квартира: комната 4x5, комната 3x4, кухня 3x3, коридор 2x3, дверь справа, 2 окна"

if __name__ == "__main__":
    from pathlib import Path
    Path("out").mkdir(exist_ok=True)
    spec = parse_request(TEXT)
    print(f"Запрос: {TEXT}")
    print(f"Комнат: {len(spec['rooms'])}, дверей: {spec['doors']}, окон: {spec['windows']}")
    from core.autocad_ai import layout
    for name, x, y, w, h in layout(spec):
        print(f"  {name:8} @ ({x:>4}, {y:>4})  {w}x{h}")
    print("DXF:", generate_dxf(spec, "out/plan.dxf"))
    print("SVG:", render_svg(spec, "out/plan.svg"))
    print("Готово: out/plan.dxf открывается в AutoCAD.")
