# -*- coding: utf-8 -*-
"""Заставка, справка и финальные экраны."""

from __future__ import annotations

from .screen import Canvas, Pal, term_size

FLAME = [
    "    ░    ",
    "   ░▒░   ",
    "  ░▒▓▒░  ",
    " ░▒▓█▓▒░ ",
    " ░▒▓█▓▒░ ",
    "  ░▒▓▒░  ",
    "   ░▒░   ",
    "    ░    ",
]

SHADE = {"░": 241, "▒": 246, "▓": 251, "█": 255}


def _flame(c: Canvas, x: int, y: int, tick: int) -> None:
    from .screen import fg

    for row, line in enumerate(FLAME):
        wobble = [0, 2, -2, 1, -1, 3][(tick + row * 2) % 6]
        for col, ch in enumerate(line):
            if ch == " ":
                continue
            base = SHADE[ch]
            shade = base if ch == "█" else max(234, min(255, base + wobble))
            c.put(x + col, y + row, ch, fg(shade))


def draw_title(c: Canvas, tick: int) -> None:
    h = c.h
    start = max(1, (h - 24) // 2)
    fx = (c.w - 9) // 2
    _flame(c, fx, start, tick)

    c.center(start + 9, "П Е П Е Л", Pal.white)
    c.center(start + 10, "монохромный рогалик", Pal.dim)

    c.center(start + 12, "─" * 27, Pal.dark)
    c.center(start + 14, "Ты спускаешься в шахту, где под пеплом", Pal.mid)
    c.center(start + 15, "спит алтарь. Семь этажей. Одна жизнь.", Pal.mid)
    c.center(start + 17, "─" * 27, Pal.dark)

    c.center(start + 19, "[ Enter ]   начать", Pal.bright)
    c.center(start + 20, "[  ?  ]   управление", Pal.mid)
    c.center(start + 21, "[  q  ]   выход", Pal.mid)

    footer = "пепел · v1.0"
    if start + 22 <= c.h - 2:
        c.center(c.h - 2, footer, Pal.faint)


def draw_help(c: Canvas) -> None:
    bw, bh = min(58, c.w - 4), 15
    x, y = (c.w - bw) // 2, (c.h - bh) // 2
    c.fill(x, y, bw, bh, " ", "")
    c.frame(x, y, bw, bh, Pal.mid)
    c.put(x + 2, y, " УПРАВЛЕНИЕ ", Pal.light)

    rows = [
        ("СТРЕЛКИ / WASD / HJKL", "движение"),
        ("1", "выпить зелье"),
        ("2", "прочесть свиток"),
        ("g", "поднять предмет"),
        (".", "подождать ход"),
        (">  или Enter", "спуститься по лестнице"),
        ("?", "эта справка"),
        ("q", "выйти из игры"),
    ]
    yy = y + 2
    for key, text in rows:
        c.put(x + 3, yy, key, Pal.white)
        c.put(x + 26, yy, text, Pal.mid)
        yy += 1
    c.put(x + 3, y + bh - 3, "Пепел не прощает жадности.", Pal.dim)
    c.put_right(x + bw - 3, y + bh - 3, "любая клавиша", Pal.faint)


def show_title(inp) -> bool:
    """True — начать игру, False — выйти."""
    tick = 0
    frame = 0
    last = None
    while True:
        w, h = term_size()
        c = Canvas(w, h)
        draw_title(c, tick)
        c.flush(clear=(w, h) != last)
        last = (w, h)
        frame += 1
        tick += 1
        if frame <= 20:
            key = inp.poll(0.07)
        else:
            key = inp.wait()
        if not key:
            continue
        if key in ("enter", " "):
            return True
        if key in ("q", "esc"):
            return False
        if key == "?":
            w, h = term_size()
            c = Canvas(w, h)
            draw_title(c, tick)
            draw_help(c)
            c.flush()
            inp.wait()


def show_result(inp, game) -> bool:
    """True — сыграть ещё раз."""
    while True:
        w, h = term_size()
        c = Canvas(w, h)
        draw_result(c, game)
        c.flush(clear=True)

        key = inp.wait()
        if key in ("enter", " "):
            return True
        if key in ("q", "esc"):
            return False


def draw_result(c: Canvas, game) -> None:
    titles = {
        "dead": ("Т Ы   С Т А Л   П Е П Л О М", Pal.white),
        "won": ("А Л Т А Р Ь   З А Ж Ж Ё Н", Pal.white),
        "left": ("Т Ы   У Ш Ё Л", Pal.mid),
    }
    flavors = {
        "dead": "Пепел принимает всех.",
        "won": "Ты вынес свет из-под земли.",
        "left": "Шахта осталась ждать.",
    }
    title, title_col = titles.get(game.state, ("", Pal.white))
    flavor = flavors.get(game.state, "")
    top = max(3, c.h // 2 - 8)

    if game.state == "won":
        c.center(top, "◆", Pal.white)
        c.center(top + 1, "▓█▓", Pal.bright)
    else:
        c.center(top, "░ ░", Pal.dim)
        c.center(top + 1, " ░ ", Pal.dark)

    c.center(top + 3, title, title_col)
    c.center(top + 5, flavor, Pal.mid)
    c.center(top + 7, "─" * 33, Pal.dark)
    p = game.player
    c.center(top + 9, f"этаж {game.depth} · уровень {p.level} · {p.gold} золота", Pal.light)
    c.center(top + 10, f"ходов {p.turns}", Pal.dim)
    c.center(top + 13, "[ Enter ]  снова      [ q ]  выход", Pal.bright)
