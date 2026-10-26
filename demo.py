# -*- coding: utf-8 -*-
"""Демо: текстовый запрос -> архитектурный план. Запуск: python demo.py"""
from core.autocad_ai import parse_request
from core.model import build_plan
from core.render import render_dxf, render_svg
from core.acad_scr import make_open_scr, make_plot_scr, save_scr

TEXT = "комната 4x5, комната 3x4, кухня 3x3, ванная 2x3, 4 двери, 2 окна"

if __name__ == "__main__":
    from pathlib import Path
    Path("out").mkdir(exist_ok=True)
    spec = parse_request(TEXT)
    print(f"Запрос: {TEXT}")
    print(f"Комнат: {len(spec['rooms'])}, дверей: {spec['doors']}, окон: {spec['windows']}")
    plan = build_plan(spec)
    dxf = render_dxf(plan, "out/plan.dxf")
    svg = render_svg(plan, "out/plan.svg")
    save_scr(make_open_scr(dxf), "out/acad_open.scr")
    save_scr(make_plot_scr(dxf, "out/plan.pdf"), "out/acad_plot.scr")
    print(f"Площадь: {plan['area']} м2, примитивов: {len(plan['prims'])}")
    print(f"DXF: {dxf}")
    print(f"SVG: {svg}")
    print("AutoCAD: out/acad_open.scr (SCRIPT) или accoreconsole /i out/plan.dxf /s out/acad_open.scr")
