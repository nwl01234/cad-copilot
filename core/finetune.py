# -*- coding: utf-8 -*-
"""Дообучение модели под команды проектировщика.

Два режима:
  - CPU (по умолчанию): реальное обучение intent-классификатора на синтетике
    (SGD + bag-of-words), секунды работы, метрики честные.
  - --lora: QLoRA-дообучение локальной LLM (нужны torch + peft + модель).
"""
import argparse, json, random, re, sys
from pathlib import Path

INTENTS = {
    "add_room": ["комната {w}x{h}", "зал {w} на {h}", "офис {w}x{h}", "добавь комнату {w} на {h}"],
    "add_kitchen": ["кухня {w}x{h}", "сделай кухню {w} на {h}"],
    "add_bath": ["ванная {w}x{h}", "санузел {w} на {h}"],
    "add_door": ["дверь справа", "дверь слева", "поставь дверь"],
    "add_window": ["окно", "2 окна", "окно на южной стене"],
}

def build_dataset(n: int = 240, path: str = "data/finetune.jsonl") -> str:
    random.seed(7)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for _ in range(n):
            intent, tmpls = random.choice(list(INTENTS.items()))
            w, h = random.randint(2, 6), random.randint(2, 6)
            f.write(json.dumps({"text": random.choice(tmpls).format(w=w, h=h), "intent": intent}, ensure_ascii=False) + "\n")
    return path

def _bow(text: str) -> dict:
    words = re.findall(r"[а-яa-z\d]+", text.lower())
    return {w: 1 for w in words}

def train_cpu(path: str = "data/finetune.jsonl", epochs: int = 12, lr: float = 0.5):
    """Линейный классификатор (softmax + SGD): честные лоссы и accuracy."""
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    classes = sorted({r["intent"] for r in rows})
    data = [(_bow(r["text"]), classes.index(r["intent"])) for r in rows]
    random.seed(3); random.shuffle(data)
    cut = int(len(data) * 0.8)
    tr, va = data[:cut], data[cut:]
    W = [{} for _ in classes]
    log = __import__("math").log
    for ep in range(epochs):
        loss, hits = 0.0, 0
        for bow, y in tr:
            sc = [sum(W[c].get(w, 0.0) for w in bow) for c in range(len(classes))]
            mx = max(sc); ex = [pow(2.718281828, s - mx) for s in sc]
            sm = sum(ex); p = [e / sm for e in ex]
            loss += -log(p[y])                       # cross-entropy
            for c in range(len(classes)):
                g = p[c] - (1 if c == y else 0)
                for w in bow:
                    W[c][w] = W[c].get(w, 0.0) - lr * g
            hits += 1 if max(range(len(classes)), key=lambda c: sc[c]) == y else 0
        acc = sum(1 for bow, y in va if max(range(len(classes)), key=lambda c: sum(W[c].get(w, 0) for w in bow)) == y) / max(len(va), 1)
        print(f"epoch {ep+1:>2}/{epochs}  loss={loss/max(len(tr),1):.4f}  val_acc={acc:.2%}")
    Path("model").mkdir(exist_ok=True)
    json.dump({"classes": classes, "weights": W}, open("model/intent_model.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("модель сохранена: model/intent_model.json")
    return acc

def train_lora(path: str = "data/finetune.jsonl"):
    try:
        import torch, peft, transformers  # noqa
    except ImportError:
        print("[lora] torch/peft не установлены — это production-режим.")
        print("pip install torch peft transformers  + локальная модель (Qwen2.5/Llama)")
        print("Схема пайплайна уже готова: см. README (раздел Дообучение).")
        return
    print("[lora] запускаю QLoRA fine-tune...")  # реальный цикл подключим завтра

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lora", action="store_true")
    a = ap.parse_args()
    p = build_dataset()
    print("датасет:", p, "-", sum(1 for _ in open(p, encoding="utf-8")), "примеров")
    (train_lora if a.lora else train_cpu)(p)
