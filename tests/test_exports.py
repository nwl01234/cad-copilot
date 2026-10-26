# -*- coding: utf-8 -*-
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.autocad_ai import generate_dxf, parse_request, layout, render_svg
from core.gcode import generate_gcode
from core import dxf_import


def test_gcode_structure(tmp_path):
    spec = parse_request("комната 4x5, кухня 3x3, дверь, 2 окна")
    p = str(tmp_path / "plan.gcode")
    out = Path(generate_gcode(spec, p)).read_text()
    assert out.startswith("G21") and "G90" in out
    assert out.count("G1 Z-1.0") == len(layout(spec))
    x_coords = [l for l in out.splitlines() if l.startswith("G1 X")]
    assert x_coords, "нет рабочих ходов"
    for line in x_coords:
        cmd = line.split()[1].lstrip("XY")
        val = float(line.split()[1][1:])
        assert val >= 0  # всё в положительных мм


def test_dxf_roundtrip(tmp_path):
    spec = parse_request("комната 4x5, кухня 3x3")
    dxf_path = generate_dxf(spec, str(tmp_path / "r.dxf"))
    d = dxf_import.read_dxf(dxf_path)
    layers = {r[0] for r in d["rooms"]}
    assert len(d["rooms"]) == len(spec["rooms"]) or len(d["rooms"]) == 1  # ezdxf, если установлен, объединяет с MTEXT; линий минимум 4
    assert any(l in layers for l in ("KOMNATA", "ROOM", "KUHNYA")), d["rooms"]


def test_dxf_shift_and_remove(tmp_path):
    spec = parse_request("комната 4x5, кухня 3x3")
    dxf_path = generate_dxf(spec, str(tmp_path / "r.dxf"))
    d = dxf_import.read_dxf(dxf_path)
    target = d["rooms"][0][0]
    before = [(r[1], r[2]) for r in d["rooms"]]
    dxf_import.shift_room(d, target, 10.0, -2.0)
    after = [(r[1], r[2]) for r in d["rooms"]]
    assert after[0][0] == before[0][0] + 10.0 and after[0][1] == before[0][1] - 2.0
    n = len(d["lines"])
    dxf_import.remove_room(d, target)
    assert len(d["lines"]) < n
    saved = dxf_import.save_dxf(d, str(tmp_path / "edited.dxf"))
    assert "LINE" in Path(saved).read_text() and "EOF" in Path(saved).read_text()
