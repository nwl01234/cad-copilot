# -*- coding: utf-8 -*-
"""CAD Copilot -> живой AutoCAD (или BricsCAD/ZWCAD: совместимый COM API).

Путь 1 из интеграции: pywin32 COM. AutoCAD запущен -> примитивы рисуются
напрямую в активном документе (слои создаются с цветами). AutoCAD не
запущен/не установлен -> понятная ошибка; в этом случае пользоваться
core/acad_scr.py (SCR/accoreconsole) или просто открыть наш DXF.

Тест покрывает логику draw_plan() через duck-typed fake Postgres-объект
(см. tests/test_acad_bridge.py), поэтому здесь нет импорта win32com
на верхнем уровне.
"""

APP_PROGIDS = ("AutoCAD.Application", "BricscadApp.AcadApplication",
               "ZWCAD.Application")

COLOR_INDEX = {  # номера цветов AutoCAD по слоям
    "Steny": 7, "Peregorodki": 8, "Okna": 4, "Dveri": 2,
    "Razmery": 3, "Explication": 7, "Titles": 7,
}


def connect(progids=APP_PROGIDS):
    """Подключиться к запущенному кад-приложению; иначе RuntimeError."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as e:
        raise RuntimeError("pywin32 не установлен: pip install pywin32") from e
    for pid in progids:
        try:
            app = win32com.client.GetActiveObject(pid)
            if app.Visible is False:
                app.Visible = True
            return app
        except Exception:
            continue
    raise RuntimeError(
        "Запущенный AutoCAD/BricsCAD/ZWCAD не найден. Запусти CAD или используй "
        "core/acad_scr.py (SCR) / открой DXF вручную (out/plan.dxf).")


def ensure_layer(doc, layer, color):
    for i in range(doc.Layers.Count):
        if doc.Layers.Item(i).Name == layer:
            return doc.Layers.Item(i)
    lay = doc.Layers.Add(layer)
    lay.color = color
    return lay


def draw_prims(doc, prims):
    """Примитивы -> COM дока. doc duck-typed: AddLine/AddArc/AddText.."""
    for lay, col in COLOR_INDEX.items():
        ensure_layer(doc, lay, col)
    n = 0
    for pr in prims:
        kind = pr[0]
        if kind == "line":
            _, lay, x1, y1, x2, y2 = pr
            doc.ActiveLayer = ensure_layer(doc, lay, COLOR_INDEX.get(lay, 7))
            doc.AddLine([x1, y1, 0.0], [x2, y2, 0.0]); n += 1
        elif kind == "arc":
            _, lay, cx, cy, r, s, e = pr
            doc.ActiveLayer = ensure_layer(doc, lay, COLOR_INDEX.get(lay, 7))
            doc.AddArc(cx, cy, r, 3.14159265359 * float(s) / 180.0,
                       3.14159265359 * float(e) / 180.0); n += 1
        elif kind == "text":
            _, lay, x, y, h, s, align = pr
            doc.ActiveLayer = ensure_layer(doc, lay, COLOR_INDEX.get(lay, 7))
            doc.AddText(s, [x, y, 0.0], h); n += 1
    return n


def draw_plan(app, plan):
    """app = COM Application: взять/создать док, нарисовать, зумить."""
    if app.Documents.Count == 0:
        app.Documents.Add()
    doc = app.ActiveDocument
    n = draw_prims(doc, plan["prims"])
    try:
        app.ZoomExtents()
    except Exception:
        pass
    return doc, n
