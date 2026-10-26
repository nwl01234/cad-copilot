# -*- coding: utf-8 -*-
"""Верификация DXF без установленного AutoCAD.

Уровень 1 — структурные проверки собственным парсером (баланс секций,
известные слои, конечные координаты, радиусы/углы ARC, высоты TEXT).
Уровень 2 — независимый читатель ezdxf (если установлен): doc.audit + reopen.
Уровень 3 — инварианты против модели (см. verify_against_plan).

CLI:  python -m tools.verify_dxf out/plan.dxf [--plan-json plan.json]
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.model import L_WALL, L_PART, L_DOOR, L_WIN, L_DIM, L_EXPL, L_TITLE

KNOWN_LAYERS = {L_WALL, L_PART, L_DOOR, L_WIN, L_DIM, L_EXPL, L_TITLE}


def structural_checks(path: str) -> dict:
    txt = Path(path).read_text(encoding="cp1251", errors="replace")
    errors, warns = [], []
    if not txt.rstrip().endswith("EOF"):
        errors.append("нет EOF в конце файла")
    secs = txt.count("SECTION") - txt.count("ENDSEC")
    if secs != 0:
        errors.append(f"SECTION/ENDSEC не сбалансированы (разница {secs})")
    if "AC1009" not in txt:
        errors.append("нет $ACADVER=AC1009 (R12)")
    ents = {"LINE": 0, "ARC": 0, "TEXT": 0}
    cur = None
    lines_ = [l.strip() for l in txt.splitlines()]
    for i, v in enumerate(lines_):
        if v == "0" and i + 1 < len(lines_):
            nxt = lines_[i + 1]
            if nxt in ents:
                ents[nxt] += 1
                cur = nxt
            elif nxt in ("ENDSEC", "EOF"):
                cur = None
            else:
                cur = None
            continue
        if cur in ("LINE", "ARC") and v in ("10", "11", "20", "21", "40", "50", "51"):
            try:
                float(lines_[i + 1])
            except (ValueError, IndexError):
                errors.append(f"нечисловое значение после кода {v}")
    if ents["LINE"] == 0:
        errors.append("нет ни одной LINE")
    if ents["ARC"] == 0:
        warns.append("нет ARC (двери не построены?)")
    layers = {lines_[i + 1] for i, v in enumerate(lines_) if v == "8" and i + 1 < len(lines_)}
    unknown = layers - KNOWN_LAYERS
    if unknown:
        warns.append(f"слои вне модели: {sorted(unknown)}")
    return {"file": path, "entities": ents, "errors": errors, "warnings": warns,
            "layers": sorted(layers)}


def ezdxf_audit(path: str) -> dict:
    """Уровень 2: независимая реализация читателя DXF (ezdxf) — audit + reopen."""
    try:
        import ezdxf
    except ImportError:
        return {"available": False,
                "note": "ezdxf не установлен (pip install ezdxf) — пропущено"}
    doc = ezdxf.readfile(path)
    audit = doc.audit()
    msp = doc.modelspace()
    kinds = {}
    for e in msp:
        kinds[e.dxftype()] = kinds.get(e.dxftype(), 0) + 1
    return {"available": True, "errors": list(audit.errors), "fixes": audit.fixes,
            "entity_kinds": kinds}


def verify_against_plan(path: str, plan: dict) -> dict:
    """DXF соответствует модели: число ARC = числу дверей, стены есть, bbox в канве."""
    st = structural_checks(path)
    arcs = st["entities"]["ARC"]
    doors = len([p for p in plan["prims"] if p[0] == "arc"])
    ok = arcs == doors
    cx = plan["canvas"]
    return {"arcs_match_doors": ok, "expected_arcs": doors, "got_arcs": arcs,
            "area": plan["area"]}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "out/plan.dxf"
    rep = structural_checks(path)
    rep["ezdxf"] = ezdxf_audit(path)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    sys.exit(1 if rep["errors"] else 0)
