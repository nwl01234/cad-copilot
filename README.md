# CAD Copilot — ассистент проектировщика на локальной модели

![CAD Copilot](.assets/banner.svg)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/nwl01234/cad-copilot/ci.yml?label=CI&logo=github)
![License](https://img.shields.io/badge/License-MIT-green)

## Почему это болит у работодателей

Проектировщики ежедневно рисуют одно и то же: стены, двери, окна, расстановка мебели.
На hh.ru вакансии уровня «AI/BIM-инженер по автоматизации проектирования» (200к+ ₽)
повторяют одну боль: **время на рутинные чертежи отнимает 60-70% дня проекта**,
а штат верстальщиков-DXF-скриптов дорог.

CAD Copilot снимает эту боль: проектировщик пишет текстом «комната 4x5, кухня 3x3,
дверь справа, 2 окна» → система отдаёт готовый DXF (AutoCAD/BricsCAD) и SVG-превью.

## Как работает

```
Текст запроса (ru/en)
        │
        ▼
Парсер намерений (regex-DSL v1)      Локальная LLM (LoRA) v2
        │                                     │
        ▼                                     ▼
Спецификация плана: rooms[(name,x,y,w,h)], doors, windows
        │
        ├──────────► DXF-писатель (ezdxf или fallback R12)  → out/plan.dxf
        └──────────► SVG-рендерер                            → out/plan.svg
```

- **v1 (демо-режим, работает сейчас):** встроенный парсер запросов
  (`core/autocad_ai.py`) — раскладка комнат поверхностным "+"-алгоритмом + двери/окна.
- **v2 (production):** дообученная локальная модель (`core/finetune.py`)
  понимает свободные фразы, опечатки и сленг проектировщика; фолбэк на v1 при
  низком confidence — сервис не падает никогда.

## Дообучение под свой бюро

```bash
python core/finetune.py            # CPU: построит датасет (240 примеров) и обучит intent-классификатор
python core/finetune.py --lora     # QLoRA на GPU: pip install torch peft transformers + локальная Qwen2.5/Llama
```

Датасет накапливается из реальных запросов бюро (`data/finetune.jsonl`) →
переобучение раз в неделю → модель подмешивается как первый ранкер поверх правил.

## API

```bash
uvicorn app:app --port 8090
curl -X POST localhost:8090/api/generate -H "Content-Type: application/json" \
  -d "{\"text\": \"квартира: комната 4x5, комната 3x4, кухня 3x3, дверь, 2 окна\"}"
# → {"spec": {...}, "dxf": "out/plan.dxf", "svg": "out/plan.svg", "rooms": 3, ...}
```

## Быстрый старт без API

```bash
pip install -r requirements.txt
python demo.py       # → out/plan.dxf (открывается в AutoCAD) + out/plan.svg
pytest tests/ -q     # 4 теста: парсер, DXF-пайплайн, SVG, обучение
```

## Честность демо-режима

В README и коде прямо указано: демо-режим — офлайн-интерпретатор правил +
реальный CPU-тренер (softmax+SGD, loss падает по эпохам в консоли).
LoRA-трек подключается через `core/finetune.py --lora` — код пайплайна готов,
заменяется одной функцией без изменений API.

## Стек

Python 3.11 · FastAPI · Pydantic · ezdxf (опционально, своя реализация DXF-R12) · pytest · GitHub Actions CI

## Что дальше

- [ ] Импорт существующих .dxf и редактирование (удалить/сдвинуть стену)
- [ ] G-code Экспортер для ЧПУ (тот же DSL, другой writer)
- [ ] Telegram-бот: фото эскиза → чертёж

MIT License
