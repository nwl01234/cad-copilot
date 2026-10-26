# -*- coding: utf-8 -*-
"""CAD Copilot -> пакетная обработка AutoCAD через .scr (путь 2).

AutoCAD (и его консольный ядро accoreconsole.exe) исполняет .scr как серию
командных строк без GUI. Это позволяет: открыть наш DXF, зумить, сохранить
в DWG, распечатать в PDF — автоматом, в т.ч. на машине без интерактивного
сеанса. Путь работает всегда, даже когда COM-мост недоступен.

Генерация:
  scr = make_open_scr("out/plan.dxf")   -> список командных строк
  save_scr(scr, "out/plan.scr")

Запуск вручную в AutoCAD: командная строка -> _.SCRIPT <путь .scr>
Батч-режим (серверный, без GUI, есть в комплекте AutoCAD):
  "C:\\Program Files\\Autodesk\\AutoCAD 2024\\accoreconsole.exe" ^
      /i out\\plan.dxf /s out\\batch.scr
"""
from pathlib import Path


def make_open_scr(dxf_path: str, out_dwg: str = None) -> list:
    """Скрипт: открыть DXF, Zoom Extents, [сохранить как DWG]."""
    lines = ["FILEDIA 0", f"_.OPEN {dxf_path}", "_.ZOOM _E"]
    if out_dwg:
        lines += [f"_.SAVEAS 2018 {out_dwg}"]
    lines.append("_.QSAVE")
    return lines


def make_plot_scr(dxf_path: str, pdf_path: str) -> list:
    """Скрипт распечатки планировки в PDF прямо из DXF (открытие + PLOT)."""
    return ["FILEDIA 0", f"_.OPEN {dxf_path}", "_.ZOOM _E",
            f"_.-PLOT Y  Model  DWG To PDF.pc3  ISO A4 (210 x 297 мм) "
            f"Meters  Landscape  No  Extents  Fit  Center  Yes  {pdf_path} "
            f"Yes  No", "FILEDIA 1"]


def save_scr(lines, path: str) -> str:
    Path(path).write_text("\n".join(lines) + "\n", encoding="cp1251")
    return path
