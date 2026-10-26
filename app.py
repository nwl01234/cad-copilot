# -*- coding: utf-8 -*-
"""CAD Copilot API: текст -> DXF + SVG превью + G-code; импорт DXF."""
from pathlib import Path
from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from core.autocad_ai import generate_dxf, parse_request, render_svg
from core.gcode import generate_gcode
from core import dxf_import

app = FastAPI(title="CAD Copilot", version="1.1.0",
              description="Текстовый запрос -> план -> DXF / SVG / G-code (ЧПУ)")
OUT = Path("out"); OUT.mkdir(exist_ok=True)

class Req(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"status": "ok", "model": "offline-fallback + intent-model"}

@app.post("/api/generate")
def generate(req: Req):
    spec = parse_request(req.text)
    dxf = generate_dxf(spec, str(OUT / "plan.dxf"))
    svg = render_svg(spec, str(OUT / "plan.svg"))
    return {"spec": spec, "dxf": dxf, "svg": svg,
            "rooms": len(spec["rooms"]), "doors": spec["doors"], "windows": spec["windows"]}

@app.get("/api/preview")
def preview():
    return FileResponse(OUT / "plan.svg", media_type="image/svg+xml")

@app.post("/api/gcode", response_class=PlainTextResponse,
          responses={200: {"content": {"text/plain": {}}}})
def gcode(req: Req):
    """Тот же запрос -> G-code для ЧПУ (мм, G21/G90)."""
    spec = parse_request(req.text)
    return Path(generate_gcode(spec, str(OUT / "plan.gcode"))).read_text()

@app.post("/api/import")
async def import_dxf(file: UploadFile):
    """Загрузить DXF назад, отредактировать (shift/remove) или повторно отрендерить."""
    data = await file.read()
    raw = OUT / "import.dxf"
    raw.write_bytes(data)
    d = dxf_import.read_dxf(str(raw))
    return {"rooms": d["rooms"], "lines": len(d["lines"]),
            "layers": sorted({l[0] for l in d["lines"]})}
