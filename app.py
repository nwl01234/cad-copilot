# -*- coding: utf-8 -*-
"""CAD Copilot API: текст -> DXF + SVG превью."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.autocad_ai import generate_dxf, parse_request, render_svg

app = FastAPI(title="CAD Copilot", version="1.0.0")
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
