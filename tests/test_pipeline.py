# syntax check для SCR + G-code (проверка на CI без AutoCAD/ЧПУ)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.acad_scr import make_open_scr, make_plot_scr, save_scr
from core.autocad_ai import parse_request
from core.model import build_plan
from core.render import render_dxf
from core.gcode import generate_gcode


def test_scr_syntax():
    scr = make_open_scr("out/plan.dxf", "out/plan.dwg")
    assert scr[0] == "FILEDIA 0"          # отключить диалоги (обязательно для батча)
    assert any(l.startswith("_.OPEN ") for l in scr)
    assert any(l.startswith("_.ZOOM") for l in scr)
    assert any(l.startswith("_.SAVEAS") for l in scr)
    plot = make_plot_scr("p.dxf", "p.pdf")
    joined = "\n".join(plot)
    assert "-PLOT" in joined and "DWG To PDF.pc3" in joined and "Extents" in joined


def test_gcode_modal_sanity(tmp_path):
    spec = parse_request("комната 4x5, кухня 3x3")
    p = generate_gcode(spec, str(tmp_path / "g.gcode"))
    txt = Path(p).read_text()
    lines = txt.splitlines()
    assert any(l.startswith("G21") for l in lines) and any(l.startswith("G90") for l in lines)
    # каждый рабочий ход G1 XY или Z-ход; G0 может быть подъёмом (только Z)
    moves = [l for l in lines if l.startswith(("G0 X", "G1 ", "G0 Z"))]
    assert moves
    for m in moves:
        toks = m.split(";")[0].split()[1:]
        assert any(t.startswith(("X", "Z")) for t in toks), m


def test_verify_dxf_roundtrip(tmp_path):
    from tools.verify_dxf import structural_checks, verify_against_plan
    plan = build_plan(parse_request("комната 4x5, кухня 3x3, 1 дверь, 1 окно"))
    dxf = render_dxf(plan, str(tmp_path / "p.dxf"))
    rep = structural_checks(dxf)
    assert not rep["errors"], rep["errors"]
    assert rep["entities"]["ARC"] == 1 and rep["entities"]["LINE"] > 10
    cmp_ = verify_against_plan(dxf, plan)
    assert cmp_["arcs_match_doors"] is True
