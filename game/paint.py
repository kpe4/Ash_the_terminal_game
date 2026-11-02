# -*- coding: utf-8 -*-
"""Отрисовка кадра игры ПЕПЕЛ."""

from __future__ import annotations

import math

from .dungeon import ALTAR, FINAL_FLOOR, FLOOR, STAIRS, WALL, wrap_text
from .entities import ITEMS
from .screen import MIN_H, MIN_W, Canvas, Pal, fg


def layout(w: int, h: int) -> dict:
    panel_w = 25
    panel_x = w - panel_w
    main_w = panel_x - 1
    log_frame_h = 6 if h < 29 else 7
    map_frame_h = h - log_frame_h
    return {
        "panel_x": panel_x,
        "panel_w": panel_w,
        "main_w": main_w,
        "log_frame_h": log_frame_h,
        "log_y": map_frame_h,
        "map_frame_h": map_frame_h,
        "map_w": main_w - 2,
        "map_h": map_frame_h - 2,
        "h": h,
    }


def _bar(c: Canvas, x: int, y: int, width: int, ratio: float,
         fill: str, empty: str) -> None:
    ratio = max(0.0, min(1.0, ratio))
    n = int(round(ratio * width))
    c.put(x, y, "█" * n + "░" * (width - n), empty)
    if n:
        c.put(x, y, "█" * n, fill)


def _row(c: Canvas, ix: int, right: int, y: int, label: str,
         value: str, value_color: str = Pal.light) -> None:
    c.put(ix, y, label, Pal.dim)
    c.put_right(right, y, value, value_color)


def render(game, w: int, h: int) -> Canvas:
    c = Canvas(w, h)
    if w < MIN_W or h < MIN_H:
        c.center(h // 2 - 2, "ОКНО СЛИШКОМ МАЛО", Pal.white)
        c.center(h // 2, f"нужно хотя бы {MIN_W} × {MIN_H}", Pal.mid)
        c.center(h // 2 + 2, "растяни терминал — пепел подождёт", Pal.dim)
        return c
    lay = layout(w, h - 1)
    _draw_map(game, c, lay)
    _draw_panel(game, c, lay)
    _draw_log(game, c, lay)
    return c


def _draw_map(game, c: Canvas, lay: dict) -> None:
    assert game.d is not None
    mw, mh = lay["main_w"], lay["map_frame_h"]
    vw, vh = lay["map_w"], lay["map_h"]
    d = game.d
    p = game.player

    c.frame(0, 0, mw, mh, Pal.dark)
    title = f" ЭТАЖ {game.depth} / {FINAL_FLOOR} "
    c.put(2, 0, title, Pal.mid)

    # камера
    if d.w <= vw:
        cam_x = -(vw - d.w) // 2
    else:
        cam_x = max(0, min(d.w - vw, p.x - vw // 2))
    if d.h <= vh:
        cam_y = -(vh - d.h) // 2
    else:
        cam_y = max(0, min(d.h - vh, p.y - vh // 2))

    def screen_pos(mx: int, my: int) -> tuple[int, int]:
        return 1 + mx - cam_x, 1 + my - cam_y

    for sy in range(vh):
        my = sy + cam_y
        if my < 0 or my >= d.h:
            continue
        for sx in range(vw):
            mx = sx + cam_x
            if mx < 0 or mx >= d.w:
                continue
            tile = d.tiles[my][mx]
            dist = math.hypot(mx - p.x, my - p.y)
            visible = (mx, my) in game.visible
            seen = (mx, my) in game.explored
            ch, col = "", ""
            if visible:
                if tile == WALL:
                    ch = "▓"
                    col = Pal.light if dist < 2.6 else (Pal.mid if dist < 4.6 else Pal.dim)
                elif tile == FLOOR:
                    ch = "·"
                    col = Pal.mid if dist < 3.2 else (Pal.dim if dist < 5.6 else Pal.dark)
                elif tile == STAIRS:
                    ch, col = ">", Pal.white
                elif tile == ALTAR:
                    if game.guardian_alive():
                        ch, col = "◊", Pal.bright
                    else:
                        ch, col = "◆", Pal.white
            elif seen:
                if tile == WALL:
                    ch, col = "▒", Pal.dark
                elif tile == FLOOR:
                    ch, col = "·", Pal.faint
                elif tile == STAIRS:
                    ch, col = ">", Pal.dim
                elif tile == ALTAR:
                    ch, col = "◊", Pal.dim
            if ch:
                c.put(1 + sx, 1 + sy, ch, col)

    # предметы
    for (mx, my), item in game.items.items():
        if (mx, my) not in game.visible:
            continue
        data = ITEMS[item["kind"]]
        sx, sy = screen_pos(mx, my)
        if 1 <= sx < mw - 1 and 1 <= sy < mh - 1:
            c.put(sx, sy, data["ch"], Pal.white)

    # чудовища
    for m in game.monsters:
        if (m.x, m.y) not in game.visible:
            continue
        sx, sy = screen_pos(m.x, m.y)
        if not (1 <= sx < mw - 1 and 1 <= sy < mh - 1):
            continue
        color = Pal.white if m.bold else fg(m.shade)
        c.put(sx, sy, m.ch, color)

    # цифры урона
    for (mx, my), text in game.fx.items():
        sx, sy = screen_pos(mx, my)
        if 1 <= sx < mw - 1 and 1 <= sy < mh - 1:
            c.put(sx, sy, text, Pal.white)

    # игрок
    sx, sy = screen_pos(p.x, p.y)
    if 1 <= sx < mw - 1 and 1 <= sy < mh - 1:
        c.put(sx, sy, "@", Pal.white)


def _draw_panel(game, c: Canvas, lay: dict) -> None:
    p = game.player
    x, y, w, h = lay["panel_x"], 0, lay["panel_w"], lay["h"]
    c.frame(x, y, w, h, Pal.dark)
    c.put(x + 2, y, " ПЕПЕЛ ", Pal.light)

    ix = x + 2
    right = x + w - 3
    bar_w = w - 5
    yy = y + 2

    c.put(ix, yy, "ЗДОРОВЬЕ", Pal.dim)
    hp_val = f"{p.hp}/{p.max_hp}"
    hp_col = Pal.white if p.hp <= p.max_hp * 0.3 else Pal.bright
    c.put_right(right, yy, hp_val, hp_col)
    _bar(c, ix, yy + 1, bar_w, p.hp / p.max_hp, hp_col, Pal.dark)
    yy += 3

    c.put(ix, yy, "ОПЫТ", Pal.dim)
    c.put_right(right, yy, f"{p.xp}/{p.next_xp}", Pal.light)
    _bar(c, ix, yy + 1, bar_w, p.xp / p.next_xp, Pal.light, Pal.dark)
    yy += 3

    c.put(ix, yy, "─" * (w - 4), Pal.dark)
    yy += 1

    _row(c, ix, right, yy, "УРОВЕНЬ", str(p.level), Pal.light)
    yy += 1
    _row(c, ix, right, yy, "ЭТАЖ", f"{game.depth} / {FINAL_FLOOR}", Pal.light)
    yy += 1
    _row(c, ix, right, yy, "АТАКА", str(p.atk), Pal.light)
    yy += 1
    _row(c, ix, right, yy, "ЗАЩИТА", str(p.defense), Pal.light)
    yy += 1
    _row(c, ix, right, yy, "ЗОЛОТО", str(p.gold), Pal.light)
    yy += 1

    c.put(ix, yy, "─" * (w - 4), Pal.dark)
    yy += 1
    _row(c, ix, right, yy, "ЗЕЛЬЯ", str(p.potions), Pal.light)
    yy += 1
    _row(c, ix, right, yy, "СВИТКИ", str(p.scrolls), Pal.light)
    yy += 1

    c.put(ix, yy, "─" * (w - 4), Pal.dark)
    yy += 1

    keys = [
        ("1", "зелье", "2", "свиток"),
        ("g", "поднять", "", ""),
        (".", "ждать", ">", "вниз"),
        ("?", "помощь", "q", "выход"),
    ]
    for k1, t1, k2, t2 in keys:
        c.put(ix, yy, k1, Pal.white if k1 else "")
        c.put(ix + 2, yy, t1, Pal.mid)
        if k2:
            c.put(ix + 10, yy, k2, Pal.white)
            c.put(ix + 12, yy, t2, Pal.mid)
        yy += 1

    # подсказка внизу панели
    hint = "найди алтарь" if game.depth >= FINAL_FLOOR else "вниз по лестнице"
    if yy <= y + h - 2:
        c.put_right(right, y + h - 2, hint, Pal.faint)


def _draw_log(game, c: Canvas, lay: dict) -> None:
    x, y = 0, lay["log_y"]
    w, h = lay["main_w"], lay["log_frame_h"]
    c.frame(x, y, w, h, Pal.dark)
    c.put(2, y, " ЖУРНАЛ ", Pal.mid)
    turn = f"ход {game.turn} "
    c.put_right(w - 2, y, turn, Pal.faint)
    inner = w - 4
    lines: list[tuple[str, str]] = []
    for text, color in game.log:
        for part in wrap_text(text, inner):
            lines.append((part, color))
    rows = h - 2
    visible = lines[-rows:]
    for i, (text, color) in enumerate(visible):
        age = len(visible) - 1 - i
        col = color if age == 0 else (Pal.dim if age >= 2 else Pal.mid)
        c.put(2, y + 1 + i, text, col)
