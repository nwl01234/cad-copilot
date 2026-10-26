# -*- coding: utf-8 -*-
"""CAD Copilot API: текст -> план (стены/двери/окна/размеры/экспликация)
-> DXF R12 + SVG + G-code + SCR-скрипт для AutoCAD; импорт DXF."""
from pathlib import Path
from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from core.autocad_ai import parse_request
from core.model import build_plan
from core.render import render_dxf, render_svg
from core.gcode import generate_gcode
from core.acad_scr import make_open_scr, make_plot_scr, save_scr
from core import dxf_import

app = FastAPI(title="CAD Copilot", version="2.0.0",
              description="NL -> архитектурный план этажа -> DXF / SVG / G-code / AutoCAD SCR")
OUT = Path("out"); OUT.mkdir(exist_ok=True)

class Req(BaseModel):
    text: str

def _plan(text: str):
    plan = build_plan(parse_request(text))
    render_dxf(plan, str(OUT / "plan.dxf"))
    render_svg(plan, str(OUT / "plan.svg"))
    for name, lines in (("acad_open.scr", make_open_scr("out/plan.dxf")),
                        ("acad_plot.scr", make_plot_scr("out/plan.dxf", "out/plan.pdf"))):
        save_scr(lines, str(OUT / name))
    return plan

@app.get("/health")
def health():
    return {"status": "ok", "engine": "wall-model (СПДС) + intent-model"}

@app.post("/api/generate")
def generate(req: Req):
    plan = _plan(req.text)
    return {"dxf": str(OUT / "plan.dxf"), "svg": str(OUT / "plan.svg"),
            "scr": [str(OUT / "acad_open.scr"), str(OUT / "acad_plot.scr")],
            "rooms": [{"№": i + 1, "name": r[0], "w": r[3], "h": r[4],
                       "area": round(r[3] * r[4], 2)} for i, r in enumerate(plan["rooms"])],
            "area_total": plan["area"],
            "prims": len(plan["prims"])}

@app.get("/api/preview")
def preview():
    return FileResponse(OUT / "plan.svg", media_type="image/svg+xml")

@app.get("/api/scr", response_class=PlainTextResponse,
         responses={200: {"content": {"text/plain": {}}}})
def scr(kind: str = "open"):
    """AutoCAD .scr: kind=open (открыть/зумить/сохранить) | plot (открыть+PDF)."""
    path = OUT / ("acad_open.scr" if kind != "plot" else "acad_plot.scr")
    if not path.exists():
        _plan("комната 4x5, комната 3x4, кухня 3x3, ванная 2x3, 4 двери, 2 окна")
    return path.read_text()

@app.post("/api/gcode", response_class=PlainTextResponse,
          responses={200: {"content": {"text/plain": {}}}})
def gcode(req: Req):
    """Контуры комнат -> G-code для ЧПУ (мм, G21/G90)."""
    spec = parse_request(req.text)
    return Path(generate_gcode(spec, str(OUT / "plan.gcode"))).read_text()

@app.post("/api/import")
async def import_dxf(file: UploadFile):
    """Загрузить DXF обратно: слои, комнаты (bbox по слоям)."""
    data = await file.read()
    raw = OUT / "import.dxf"
    raw.write_bytes(data)
    d = dxf_import.read_dxf(str(raw))
    return {"rooms": d["rooms"], "lines": len(d["lines"]),
            "layers": sorted({l[0] for l in d["lines"]})}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8090)
