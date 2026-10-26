# -*- coding: utf-8 -*-
"""Тесты архитектурной модели, рендеров и CAD-мостов."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.autocad_ai import parse_request
from core.model import build_plan, EW, IW, STAGES
from core.render import render_dxf, render_svg
from core import acad_bridge, acad_scr

SPEC = "комната 4x5, комната 3x4, кухня 3x3, ванная 2x3, 4 двери, 2 окна"


def test_plan_geometry():
    plan = build_plan(parse_request(SPEC))
    assert plan["area"] == 47.0 and len(plan["prims"]) > 50
    assert len([p for p in plan["prims"] if p[0] == "arc"]) == 4  # 4 дуги дверей


def test_wall_thickness():
    """Наружная стена толще перегородки: линии EW на / IW."""
    plan = build_plan(parse_request(SPEC))
    ew_lines = [(p[3], p[2]) for p in plan["prims"] if p[0] == "line" and p[1] == "Steny"]
    assert ew_lines, "нет наружных стен"
    # x=0 наружная: лицевая 0, внутренняя 0.3
    assert any(abs(a - 0.3) < 1e-6 and abs(b) < 1e-6 for a, b in ew_lines)


def test_door_openings_cut_walls():
    """В стене с дверью есть разрыв (сегменты не сшиваются по всей длине)."""
    plan = build_plan(parse_request("комната 4x5, 1 дверь"), stages=("walls", "doors"))
    bottom = [p for p in plan["prims"] if p[0] == "line" and p[4] == 0.0 and p[5] == 0.0
              and abs(p[3] - p[5]) < 1e-9 and p[1] in ("Steny", "Peregorodki")]
    # у нижней стены комната 4x5: разрыв 0.9 -> не должно быть линии 0..4
    full = [p for p in bottom if abs(p[2] - 0) < 1e-9 and abs(p[4] - 4.0) < 1e-9]
    assert not full, "проём двери не вырезан"


def test_windows_glass_and_jambs():
    plan = build_plan(parse_request(SPEC), stages=("walls", "windows"))
    glass = [p for p in plan["prims"] if p[0] == "line" and p[1] == "Okna"]
    assert len(glass) == 2  # 2 окна
    for g in glass:
        assert abs(g[3] - g[5]) < 1e-9  # горизонтальное стекло


def test_dxf_and_svg_consistency(tmp_path):
    plan = build_plan(parse_request(SPEC))
    dxf = Path(render_dxf(plan, str(tmp_path / "p.dxf")))
    svg = Path(render_svg(plan, str(tmp_path / "p.svg")))
    txt = dxf.read_text(encoding="cp1251")
    assert "AC1009" in txt and "Steny" in txt and "ARC" in txt
    body = svg.read_text(encoding="utf-8")
    assert body.count("<path") == sum(1 for p in plan["prims"] if p[0] == "arc")
    assert "Площадь, м2" in body


class FakeDoc:
    """Duck-typed COM: собирает вызовы, чтобы тестить мост без AutoCAD."""
    def __init__(self):
        self.calls = []
        from collections import namedtuple
        self.Layers = FakeLayers()
        self._layer = None

    def AddLine(self, a, b):
        self.calls.append(("line", tuple(a), tuple(b)))

    def AddArc(self, cx, cy, r, s, e):
        self.calls.append(("arc", cx, cy, r, round(s, 3), round(e, 3)))

    def AddText(self, s, pt, h):
        self.calls.append(("text", s, tuple(pt), h))


class FakeLayer:
    def __init__(self, name):
        self.Name = name
        self.color = 0


class FakeLayers:
    def __init__(self):
        self.items = []
        self.Count = 0

    def Add(self, name):
        lay = FakeLayer(name)
        self.items.append(lay)
        return lay

    def Item(self, i):
        return self.items[i]


class FakeApp:
    def __init__(self):
        self.doc = FakeDoc()
        self.doc.Layers = FakeLayers()
        self.doc.ActiveLayer = None
        self.Documents = FakeDocs(self.doc)
        self.ActiveDocument = self.doc

    def ZoomExtents(self):
        self.doc.calls.append(("zoom",))


class FakeDocs:
    def __init__(self, doc):
        self._doc = doc

    def Add(self):
        return self._doc

    @property
    def Count(self):
        return 1

    @property
    def ActiveDocument(self):
        return self._doc

    @property
    def ActiveDocument(self):
        return self._doc


def test_com_bridge_draw_plan():
    plan = build_plan(parse_request(SPEC))
    app = FakeApp()
    doc, n = acad_bridge.draw_plan(app, plan)
    assert n == len(plan["prims"])
    assert len(doc.calls) == len(plan["prims"]) + 1  # примитивы + ZoomExtents
    arcs = [c for c in doc.calls if c[0] == "arc"]
    assert len(arcs) == 4 and round(arcs[0][3], 2) == 0.9
    texts = [c for c in doc.calls if c[0] == "text"]
    assert any("ПЛАН" in t[1] for t in texts)


def test_scr_generation():
    scr = acad_scr.make_open_scr("out/plan.dxf", "out/plan.dwg")
    assert "FILEDIA 0" == scr[0] and "_.OPEN out/plan.dxf" in "\n".join(scr)
    plot = acad_scr.make_plot_scr("out/plan.dxf", "out/plan.pdf")
    assert "-PLOT" in "\n".join(plot) and "plan.pdf" in "\n".join(plot)
    p = acad_scr.save_scr(scr, str(tmp_scr_path()))
    assert Path(p).read_text().startswith("FILEDIA 0")


def tmp_scr_path():
    import tempfile
    d = tempfile.mkdtemp()
    return Path(d) / "plan.scr"
