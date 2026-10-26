# -*- coding: utf-8 -*-
"""CAD Copilot: архитектурная модель плана этажа (СПДС-совместимая).

Единицы — метры, ось Y вверх (как в AutoCAD). Модель выдаёт список примитивов
(``line`` / ``arc`` / ``text``) на именованных слоях; DXF и SVG рендеры — два
бэкенда над одним и тем же набором примитивов (единый источник истины).

Учитывается:
  * стены двумя линиями с толщиной: наружные EW, перегородки IW;
  * проёмы: разрыв в обеих линиях стены + четверти (impostы) по краям;
  * двери: проём 0.9 м + дуга открывания (ARC) + полотно;
  * окна: проём 1.3 м + стекло в середине толщины стены + четверти;
  * размерные цепочки по нижней и левой границе с засечками (ГОСТ Р 21.1101),
    плюс общая цепочка;
  * экспликация помещений (ГОСТ 21.501): №, наименование, площадь;
  * название чертежа над изображением, масштаб 1:100.
"""
from core.autocad_ai import layout

EW, IW = 0.30, 0.10          # толщины: наружная стена / перегородка
DOOR_W, WIN_W = 0.90, 1.30   # проёмы
TXT_H, TITLE_H = 0.25, 0.50  # высоты текста (2.5 мм на М 1:100, ГОСТ 2.304)

L_WALL, L_PART = "Steny", "Peregorodki"
L_DOOR, L_WIN = "Dveri", "Okna"
L_DIM, L_EXPL, L_TITLE = "Razmery", "Explication", "Titles"

STAGES = ("walls", "doors", "windows", "marks", "dims", "expl", "title")


def build_plan(spec: dict, stages=None) -> dict:
    """spec -> план. stages None = все; для анимокадров передают подмножество."""
    st = set(STAGES) if stages is None else set(stages)
    rooms = layout(spec)
    x0, y0 = min(r[1] for r in rooms), min(r[2] for r in rooms)
    x1, y1 = max(r[1] + r[3] for r in rooms), max(r[2] + r[4] for r in rooms)
    bbox = (x0, y0, x1, y1)
    p = []  # примитивы

    def line(lay, a, b, c, d):
        p.append(("line", lay, a, b, c, d))

    def arc(lay, cx, cy, r, s, e):
        p.append(("arc", lay, cx, cy, r, s, e))

    def text(lay, x, y, h, s, align="l"):
        p.append(("text", lay, x, y, h, str(s), align))

    def door_gaps(rooms):
        """Проёмы дверей по внутренним рёбрам комнат."""
        d = int(spec.get("doors") or 0)
        out = []
        for room in sorted(rooms, key=lambda r: -(r[3] * r[4])):
            for edge in ("bottom", "left", "top"):
                if not external(room, edge, bbox):
                    a = room[1] + 0.25 if edge in ("bottom", "top") else room[2] + 0.25
                    out.append((room, edge, (a, a + DOOR_W)))
                    break
            if len(out) >= d:
                break
        return out

    def window_gaps(rooms):
        """Окна по внешним рёбрам (top нужнее всего)."""
        k = int(spec.get("windows") or 0)
        out = []
        for room in rooms:
            for pref in ("top", "bottom", "left", "right"):
                if external(room, pref, bbox):
                    ax = room[1] if pref in ("top", "bottom") else room[2]
                    b = room[3] if pref in ("top", "bottom") else room[4]
                    u = ax + b / 2
                    out.append((room, pref, (u - WIN_W / 2, u + WIN_W / 2)))
                    break
            if len(out) >= k:
                break
        return out

    def external(room, edge, bb):
        name, x, y, w, h = room
        return {"bottom": y == bb[1], "top": y + h == bb[3],
                "left": x == bb[0], "right": x + w == bb[2]}[edge]

    # --- стены -------------------------------------------------------------
    door_list = door_gaps(rooms) if "doors" in st else []
    win_list = window_gaps(rooms) if "windows" in st else []
    dgaps = {}
    for room, edge, g in door_list:
        dgaps.setdefault((room, edge), []).append(g)
    wgaps = {}
    for room, edge, g in win_list:
        wgaps.setdefault((room, edge), []).append(g)

    if "walls" in st:
        for room in rooms:
            name, x, y, w, h = room
            for edge in ("bottom", "top", "left", "right"):
                ext = external(room, edge, bbox)
                t = EW if ext else IW
                lay = L_WALL if ext else L_PART
                horiz = edge in ("bottom", "top")
                n = (-1 if edge in ("top", "right") else 1)
                if horiz:
                    f = y if edge == "bottom" else y + h
                    u0, u1 = x, x + w
                    fix = lambda u, off=0: (u, f + off)
                else:
                    f = x if edge == "left" else x + w
                    u0, u1 = y, y + h
                    fix = lambda u, off=0: (f + off, u)
                gaps = sorted(dgaps.get((room, edge), []) + wgaps.get((room, edge), []))
                segs, cur = [], u0
                for ga, gb in gaps:
                    if gb <= cur or ga >= u1:
                        continue
                    if ga > cur:
                        segs.append((cur, ga))
                    cur = max(cur, gb)
                if cur < u1:
                    segs.append((cur, u1))
                for s0, s1 in segs:
                    line(lay, *fix(s0), *fix(s1))                       # лицевая
                    line(lay, *fix(s0, t * n), *fix(s1, t * n))         # внутренняя
                for ga, gb in gaps:
                    for u in (ga, gb):                                  # четверти
                        line(lay, *fix(u), *fix(u, t * n))

    # --- двери -------------------------------------------------------------
    if "doors" in st:
        for room, edge, (ga, gb) in door_list:
            name, x, y, w, h = room
            t = EW if external(room, edge, bbox) else IW
            if edge == "bottom":
                H, leaf, ang_g, ang_n = (ga, y + t), (0, 1), 0, 90
            elif edge == "top":
                H, leaf, ang_g, ang_n = (ga, y + h - t), (0, -1), 0, 270
            elif edge == "left":
                H, leaf, ang_g, ang_n = (x + t, ga), (1, 0), 90, 0
            else:
                H, leaf, ang_g, ang_n = (x + w - t, ga), (-1, 0), 90, 180
            if (ang_n - ang_g) % 360 == 90:
                s, e = ang_g, ang_n
            else:
                s, e = ang_n, ang_g
            line(L_DOOR, H[0], H[1], H[0] + leaf[0] * DOOR_W, H[1] + leaf[1] * DOOR_W)
            arc(L_DOOR, H[0], H[1], DOOR_W, s, e)

    # --- окна: стекло ------------------------------------------------------
    if "windows" in st:
        for room, edge, (ga, gb) in win_list:
            name, x, y, w, h = room
            horiz = edge in ("bottom", "top")
            t = EW if external(room, edge, bbox) else IW
            if horiz:
                yf = y if edge == "bottom" else y + h
                ny = 1 if edge == "bottom" else -1
                line(L_WIN, ga, yf + ny * t / 2, gb, yf + ny * t / 2)
            else:
                xf = x if edge == "left" else x + w
                nxn = 1 if edge == "left" else -1
                line(L_WIN, xf + nxn * t / 2, ga, xf + nxn * t / 2, gb)

    # --- размеры ------------------------------------------------------------
    if "dims" in st:
        def chain(pts, vertical, offsets):
            dim0, dim1 = offsets
            for off in offsets:
                if not vertical:
                    line(L_DIM, pts[0], bbox[1] - off, pts[-1], bbox[1] - off)
                else:
                    line(L_DIM, bbox[0] - off, pts[0], bbox[0] - off, pts[-1])
            for uu in pts:
                if not vertical:
                    line(L_DIM, uu, bbox[1], uu, bbox[1] - dim1 - 0.15)
                    line(L_DIM, uu - 0.08, bbox[1] - dim0 + 0.08,
                         uu + 0.08, bbox[1] - dim0 - 0.08)
                else:
                    line(L_DIM, bbox[0], uu, bbox[0] - dim1 - 0.15, uu)
                    line(L_DIM, bbox[0] - dim0 + 0.08, uu - 0.08,
                         bbox[0] - dim0 - 0.08, uu + 0.08)
            for q in range(len(pts) - 1):
                mid = (pts[q] + pts[q + 1]) / 2
                val = "%g" % round(pts[q + 1] - pts[q], 2)
                if pts[q + 1] - pts[q] < 0.35:
                    continue
                if not vertical:
                    text(L_DIM, mid, bbox[1] - dim0 + 0.10, TXT_H, val, "c")
                else:
                    text(L_DIM, bbox[0] - dim0 - 0.35, mid - 0.12, TXT_H, val, "c")
        bnd_x = sorted({bbox[0], bbox[2]} |
                       {r[1] for r in rooms if r[2] == bbox[1]} |
                       {r[1] + r[3] for r in rooms if r[2] == bbox[1]})
        bnd_y = sorted({bbox[1], bbox[3]} |
                       {r[2] for r in rooms if r[1] == bbox[0]} |
                       {r[2] + r[4] for r in rooms if r[1] == bbox[0]})
        chain(bnd_x, False, (0.8, 1.8))
        chain(bnd_y, True, (0.8, 1.8))

    # --- маркировка: № и площадь в каждой комнате ---------------------------
    if "marks" in st:
        for i, r in enumerate(rooms):
            cx_, cy_ = r[1] + r[3] / 2, r[2] + r[4] / 2
            text(L_EXPL, cx_, cy_ - 0.05, 0.35, i + 1, "c")
            text(L_EXPL, cx_, cy_ - 0.5, TXT_H, "%g м2" % round(r[3] * r[4], 2), "c")

    # --- экспликация --------------------------------------------------------
    if "expl" in st:
        xt = bbox[2] + 1.6
        yt = bbox[3]
        rh = 0.55
        cols = [0, 0.7, 2.9, 4.5]
        for c in cols:
            line(L_EXPL, xt + c, yt, xt + c, yt - rh * (len(rooms) + 1))
        for i in range(len(rooms) + 1):
            yy = yt - rh * i
            line(L_EXPL, xt, yy, xt + cols[-1], yy)
        for j, s in enumerate(["№", "Наименование", "Площадь, м²"]):
            text(L_EXPL, xt + cols[j] + 0.08, yt - 0.36, TXT_H, "Площадь, м2" if j == 2 else s)
        for i, r in enumerate(sorted(rooms, key=lambda q: -q[3] * q[4])):
            yy = yt - rh * (i + 2) + 0.14
            text(L_EXPL, xt + 0.08, yy, TXT_H, i + 1)
            text(L_EXPL, xt + cols[1] + 0.08, yy, TXT_H, r[0])
            text(L_EXPL, xt + cols[2] + 0.08, yy, TXT_H, "%g" % round(r[3] * r[4], 2))

    # --- название -----------------------------------------------------------
    if "title" in st:
        text(L_TITLE, (bbox[0] + bbox[2]) / 2, bbox[3] + 0.9, TITLE_H,
             "ПЛАН ЭТАЖА, М 1:100", "c")

    canvas = (bbox[0] - 2.5, bbox[1] - 2.5, bbox[2] + 7.0, bbox[3] + 2.0)
    return {"bbox": bbox, "canvas": canvas, "prims": p, "rooms": rooms,
            "area": round(sum(r[3] * r[4] for r in rooms), 2)}
