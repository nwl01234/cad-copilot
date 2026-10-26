# -*- coding: utf-8 -*-
"""End-to-end проверка НА машине с AutoCAD (запускать там, где он установлен).

Что делает:
  1. генерирует план и DXF/SCR тем же пайплайном, что и сервис;
  2. ищет accoreconsole.exe (консольное ядро AutoCAD, ставится с ним же);
  3. прогоняет батч: OPEN DXF -> ZOOM -> SAVEAS DWG  (реальный AutoCAD-парсер!);
  4. проверяет, что DWG создан и свежее DXF;
  5. (опция --plot) делает PDF через -PLOT;
  6. печатает PASS/FAIL и код выхода: 0 = AutoCAD реально съел наш DXF.

Запуск на машине с AutoCAD:
  python tools/e2e_autocad.py            # найдёт accoreconsole по умолчанию
  python tools/e2e_autocad.py --acad "D:\\CAD\\accoreconsole.exe" --plot
"""
import argparse
import glob
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.autocad_ai import parse_request
from core.model import build_plan
from core.render import render_dxf
from core.acad_scr import make_open_scr, make_plot_scr, save_scr

DEFAULT_GLOBS = [
    r"C:\Program Files\Autodesk\AutoCAD 20*\accoreconsole.exe",
    r"C:\Program Files\Autodesk\AutoCAD*\accoreconsole.exe",
    r"C:\Program Files\Autodesk\AutoCAD LT 20*\accoreconsole.exe",
    r"D:\Program Files\Autodesk\AutoCAD*\accoreconsole.exe",
]


def find_accoreconsole(explicit=None) -> str:
    if explicit:
        assert Path(explicit).exists(), f"не найден: {explicit}"
        return explicit
    for pat in DEFAULT_GLOBS:
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    raise FileNotFoundError("accoreconsole.exe не найден; передай --acad <путь>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acad", help="путь к accoreconsole.exe")
    ap.add_argument("--plot", action="store_true", help="также PDF через -PLOT")
    ap.add_argument("--text", default="комната 4x5, комната 3x4, кухня 3x3, ванная 2x3, 4 двери, 2 окна")
    args = ap.parse_args()

    out = Path("out/e2e"); out.mkdir(parents=True, exist_ok=True)
    spec = parse_request(args.text)
    plan = build_plan(spec)
    dxf = render_dxf(plan, str(out / "plan.dxf"))
    dwg = str(out / "plan.dwg")

    exe = find_accoreconsole(args.acad)
    scr = save_scr(make_open_scr(dxf, dwg), str(out / "open.scr"))
    print(f"[1] accoreconsole: {exe}")
    print(f"[2] план: {plan['area']} м2, примитивов: {len(plan['prims'])}, DXF: {dxf}")

    t0 = time.time()
    r = subprocess.run([exe, "/i", dxf, "/s", scr], capture_output=True, text=True,
                       timeout=300, errors="replace")
    print(f"[3] accoreconsole exit={r.returncode} ({time.time()-t0:.1f}s)")
    tail = (r.stdout or "").splitlines()[-6:]
    for ln in tail:
        print("    |", ln)

    ok = r.returncode == 0 and Path(dwg).exists() and Path(dwg).stat().st_size > 100
    print(f"[4] DWG: {dwg} -> {'OK' if ok else 'FAIL'}")
    if args.plot:
        pdf = str(out / "plan.pdf")
        scr2 = save_scr(make_plot_scr(dxf, pdf), str(out / "plot.scr"))
        r2 = subprocess.run([exe, "/i", dxf, "/s", scr2], capture_output=True,
                            text=True, timeout=300, errors="replace")
        ok = ok and Path(pdf).exists() and Path(pdf).stat().st_size > 1000
        print(f"[5] PDF: {pdf} -> {'OK' if Path(pdf).exists() else 'FAIL'}")
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
