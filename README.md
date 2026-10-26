# CAD Copilot — генерация DXF-чертежей по текстовому запросу

![CAD Copilot](.assets/banner.svg)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/nwl01234/cad-copilot/ci.yml?label=CI&logo=github)
![License](https://img.shields.io/badge/License-MIT-green)

## Что внутри

| Модуль | Что делает |
|---|---|
| `core/autocad_ai.py` | офлайн-движок: парсер запроса → спецификация → раскладка → DXF + SVG |
| `core/finetune.py` | генерация датасета, обучение intent-классификатора (CPU), сохранение модели |
| `app.py` | FastAPI: `/api/generate`, `/api/preview`, `/health` |
| `demo.py` | end-to-end прогон без сервера: текст → `out/plan.dxf` + `out/plan.svg` |
| `tests/test_core.py` | 4 теста: парсер, DXF-пайплайн, SVG, обучение |

## Пайплайн: запрос → чертёж

```
"комната 4x5, комната 3x4, кухня 3x3, дверь, 2 окна"
     │  parse_request(): regex-парсер комнат/дверей/окон
     ▼
spec = {"rooms": [("комната", 4, 5), ("комната", 3, 4), ("кухня", 3, 3)],
        "doors": 1, "windows": 2}
     │  layout(): упаковка комнат в контейнер 12 м (строки, перенос)
     ▼
[(name, x, y, w, h), ...]
     ├─ generate_dxf() → out/plan.dxf   DXF R12, слой = имя комнаты (транслит)
     └─ render_svg()   → out/plan.svg   превью для отчётов и фронта
```

DXF-writer написан без зависимостей: формируется секция ENTITIES по протоколу
R12 (LINE/TEXT, коды 0/8/10/11/20/21/40/1), слой записывается в
ASCII-транслитерации. Если установлен `ezdxf` — используется он, формат совместим.

## Модель и обучение

`python core/finetune.py` — реальное CPU-обучение, не заглушка:

1. **Датасет**: генерация 240 примеров на 5 интентов
   (`add_room`, `add_kitchen`, `add_bath`, `add_door`, `add_window`)
   из шаблонов с рандомными размерами → `data/finetune.jsonl`.
2. **Признаки**: bag-of-words, словарь собирается по всей выборке.
3. **Модель**: softmax-классификатор (вес на пару «класс×слово»), SGD, lr=0.5.
4. **Сплит**: 80/20 (seed=3), shuffle.
5. **За каждую эпоху**: кросс-энтропийный лосс и val accuracy печатаются в stdout.
6. **Артефакт**: `model/intent_model.json` (мапа класс → {слово: вес}).

Сервис при этом живёт на правилах: модель будет подмешиваться как дополнительный
ранкер поверх офлайн-парсера, без даунтайма.

`--lora` — QLoRA-трек: `pip install torch peft transformers` + локальная модель
(Qwen2.5/Llama). Код пайплайна вызова готов (core/finetune.py: train_lora),
при отсутствии GPU/peft сервис продолжает работать на офлайн-движке.

## API

```bash
uvicorn app:app --port 8090

# сгенерировать чертёж из запроса
curl -X POST localhost:8090/api/generate -H "Content-Type: application/json" \
  -d "{\"text\": \"квартира: комната 4x5, кухня 3x3, дверь, 2 окна\"}"
# → {"spec": {...}, "dxf": "out/plan.dxf", "svg": "out/plan.svg", "rooms": 2, ...}

# получить SVG-превью последнего чертежа
curl localhost:8090/api/preview -o plan.svg
```

## Запуск

```bash
pip install -r requirements.txt
python demo.py        # → out/plan.dxf (открывается в AutoCAD/BricsCAD) + out/plan.svg
pytest tests/ -q      # 4 теста: парсер, раскладка+DXF, SVG, обучение
```

## Что дальше

- [ ] Импорт и редактирование существующих `.dxf` (удаление/сдвиг стен)
- [ ] G-code-экспортер для ЧПУ (тот же DSL, другой writer)
- [ ] Telegram-бот: фото эскиза → чертёж
- [ ] Полный LoRA-трек: подключение обученного адаптера к локальной LLM через llama.cpp

MIT License
