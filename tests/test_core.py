import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core.autocad_ai import generate_dxf, layout, parse_request, render_svg
from core.finetune import build_dataset, train_cpu


def test_parse_request():
    spec = parse_request("комната 4x5, кухня 3x3, дверь, 2 окна")
    assert len(spec["rooms"]) == 2 and spec["doors"] == 1 and spec["windows"] == 2


def test_layout_and_dxf(tmp_path):
    spec = parse_request("комната 4x5, комната 3x4, коридор 2x3")
    rooms = layout(spec)
    assert len(rooms) == 3
    dxf = generate_dxf(spec, str(tmp_path / "plan.dxf"))
    assert Path(dxf).exists() and "ENTITIES" in Path(dxf).read_text(encoding="ascii")


def test_svg(tmp_path):
    spec = parse_request("комната 4x5")
    svg = render_svg(spec, str(tmp_path / "p.svg"))
    assert "<svg" in Path(svg).read_text(encoding="utf-8")


def test_finetune_runs(tmp_path):
    ds = build_dataset(30, str(tmp_path / "ds.jsonl"))
    assert Path(ds).exists()
    train_cpu(ds, epochs=2)
    assert Path("model/intent_model.json").exists()
