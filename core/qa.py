# -*- coding: utf-8 -*-
"""QA данных и модели: honeypot-выборка, consistency датасета, eval обученной модели."""
import json, re
from pathlib import Path

try:
    from core.finetune import build_dataset, train_cpu
    from core.autocad_ai import parse_request
except ImportError:  # запуск как скрипт: python core/qa.py
    from finetune import build_dataset, train_cpu
    from autocad_ai import parse_request

# фиксированные honeypot-примеры (заранее известно правильное поведение)
HONEYPOTS = [
    ("комната 3x4 дверь окно", 1, 1),
    ("кухня 2x2", 1, 0),
    ("зал 5x4 вход и выход", 1, 0),
]

def dataset_consistency(path: str = "data/finetune.jsonl") -> dict:
    """Качество разметки: все записи с непустым intent, без конфликтных дубликатов."""
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    by_text = {}
    for r in rows:
        by_text.setdefault(r["text"], set()).add(r["intent"])
    conflicts = sum(1 for s in by_text.values() if len(s) > 1)
    return {"rows": len(rows), "unique": len(by_text), "conflicts": conflicts,
            "valid": conflicts == 0}

def honeypot_check() -> dict:
    """Детерминированные примеры: парс выдаёт ожидаемое количество комнат/окон."""
    out = []
    for text, exp_rooms, exp_wins in HONEYPOTS:
        spec = parse_request(text)
        ok = (len(spec["rooms"]) == exp_rooms and spec["windows"] == exp_wins)
        out.append({"text": text, "expected_rooms": exp_rooms,
                    "got_rooms": len(spec["rooms"]), "expected_windows": exp_wins,
                    "got_windows": spec["windows"], "pass": ok})
    return {"case_count": len(out), "pass_rate": sum(1 for o in out if o["pass"]) / len(out),
            "cases": out}

def eval_trained_model(epochs: int = 3) -> dict:
    """Полный data-цикл: разметка → консистентность → обучение → eval on honeypots."""
    build_dataset(120)
    ds = dataset_consistency()
    train_cpu("data/finetune.jsonl", epochs=epochs)
    model = json.load(open("model/intent_model.json", encoding="utf-8"))
    report = {"data_consistency": ds, "honeypots": honeypot_check(),
              "model_classes": model["classes"],
              "artefact": "model/intent_model.json"}
    Path("data/qa_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(eval_trained_model(), ensure_ascii=False, indent=1)[:600])
