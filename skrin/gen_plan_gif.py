# -*- coding: utf-8 -*-
"""GIF/превью из реальной архитектурной модели: кадры = этапы build_plan(),
рендер каждого кадра — headless Edge (SVG -> PNG), сборка Pillow."""
import subprocess, sys, time
from pathlib import Path
from PIL import Image
sys.path.insert(0, ".")
from core.autocad_ai import parse_request
from core.model import build_plan, STAGES
from core.render import render_svg

TMP = Path("out/gif"); TMP.mkdir(parents=True, exist_ok=True)
spec = parse_request("комната 4x5, комната 3x4, кухня 3x3, ванная 2x3, 4 двери, 2 окна")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
progressive = [STAGES[:i + 1] for i in range(len(STAGES))]

pngs = []
for i, stages in enumerate(progressive):
    plan = build_plan(spec, stages=stages)
    render_svg(plan, str(TMP / f"s{i}.svg"))
    url = (TMP / f"s{i}.svg").resolve().as_uri()
    out = (TMP / f"s{i}.png").resolve()
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--screenshot={out}", "--window-size=955,610",
                    "--force-device-scale-factor=1", url],
                   capture_output=True, timeout=60)
    time.sleep(1.0)
    assert out.exists(), f"нет кадра {i}"
    pngs.append(Image.open(out).convert("P", palette=Image.ADAPTIVE, colors=128))

durs = [900] * len(pngs); durs[-1] = 2800
pngs[0].save("skrin/plan_v2.gif", save_all=True, append_images=pngs[1:],
             duration=durs, loop=0)
pngs[-1].resize((716, 458), Image.LANCZOS).save("skrin/plan_v2.png", optimize=True)
print("frames:", len(pngs))
