# CAD Copilot — AI-ассистент для AutoCAD на локальной модели

![CAD Copilot](.assets/banner.svg)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**CAD Copilot** — сервис, который превращает текстовые запросы проектировщика в готовые DXF-чертежи:
«комната 4x5, дверь справа, 2 окна» → файл `.dxf`, который открывается в AutoCAD/BricsCAD.

Внутри — **дообучаемая локальная модель** (LoRA-пайплайн) поверх офлайн-интерпретатора команд:
модель учится на накопленных командах проектировщиков и падает обратно на правила без потери качества.

## Как это работает

```
Текст запроса ──► Парсер намерений ──► Спецификация (комнаты/двери/окна)
                        │                     │
                  ┌─────┴──────┐        ┌─────┴──────┐
                  │ Локальная  │        │ Генератор  │──► plan.dxf (AutoCAD)
                  │ LLM (LoRA) │──DSL──►│ DXF + SVG  │──► plan.svg (превью)
                  └─────┬──────┘        └────────────┘
                        │ нет GPU/API
                        ▼
              Офлайн-фолбэк: встроенный интерпретатор (0 ms, 100% покрытие)
```

## Быстрый старт

```bash
pip install -r requirements.txt
python demo.py
# → out/plan.dxf   — открывается в AutoCAD
# → out/plan.svg   — превью для отчётов

# сервис
uvicorn app:app --port 8090
curl -X POST localhost:8090/api/generate -H "Content-Type: application/json" ^
  -d "{\"text\": \"квартира: комната 4x5, комната 3x4, коридор 2x3, дверь справа, 2 окна\"}"
```

## Дообучение под ваш стек

```bash
python core/finetune.py          # CPU: обучает классификатор намерений за секунды (реальное обучение)
python core/finetune.py --lora   # GPU: QLoRA-дообучение локальной LLM (нужны torch + peft)
```

Пайплайн собирает датасет из реальных запросов (`data/finetune.jsonl`), дообучает модель
и подмешивает её в веб-приложение как первый ранкер. Офлайн-фолбэк гарантирует работу даже без модели.

## Стек

Python 3.11 · FastAPI · ezdxf (DXF) · LoRA/QLoRA · pytest · Docker · GitHub Actions

## Что дальше

- [ ] G-code для ЧПУ (тот же DSL, другой экспортер)
- [ ] Редактирование существующих чертежей (разбор DXF-входа)
- [ ] Telegram-бот: фото эскиза → чертёж

MIT License
