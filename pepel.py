from __future__ import annotations

import random
import sys
from collections import deque

from game.dungeon import FINAL_FLOOR, STAIRS, build_dungeon
from game.game import Game
from game.paint import layout, render
from game.screen import (
    MIN_H,
    MIN_W,
    Canvas,
    Input,
    enter_alt_screen,
    leave_alt_screen,
    setup_terminal,
    term_size,
)
from game.screens import draw_help, show_result, show_title


def help_overlay(game, inp) -> None:
    w, h = term_size()
    c = render(game, w, h)
    draw_help(c)
    c.flush()
    inp.wait()


def run_game(inp, game: Game) -> str:
    last = None
    while game.state == "play":
        w, h = term_size()
        c = render(game, w, h)
        c.flush(clear=(w, h) != last)
        last = (w, h)

        key = inp.wait()
        if w < MIN_W or h < MIN_H:
            key = inp.poll(0.3)
            if not key:
                continue
        if key in ("q", "esc"):
            game.state = "left"
            break
        if key == "?":
            help_overlay(game, inp)
            continue
        if key == "enter" and game.tile(game.player.x, game.player.y) == STAIRS:
            key = ">"
        game.try_action(key)
    return game.state


def play(inp: Input) -> None:
    rng = random.Random()
    while True:
        if not show_title(inp):
            return
        game = Game(rng)
        run_game(inp, game)
        if not show_result(inp, game):
            return


def demo() -> None:
    setup_terminal()
    w, h = 100, 30
    if len(sys.argv) > 2 and "x" in sys.argv[2]:
        try:
            w, h = (int(v) for v in sys.argv[2].split("x", 1))
        except ValueError:
            pass
    lay = layout(w, h - 1)
    rng = random.Random(7)
    game = Game(rng)
    game.new_level(view=(lay["map_w"], lay["map_h"]))
    game.explored = {(x, y) for y in range(game.d.h) for x in range(game.d.w)}
    game.visible = set(game.explored)
    game.msg("Ты спускаешься в шахту. Пепел хрустит под ногами.", "\x1b[38;5;246m")
    game.msg("Где-то впереди капает вода.", "\x1b[38;5;241m")
    if game.monsters:
        m = game.monsters[0]
        game.fx[(m.x, m.y)] = "-4"
        game.msg(f"Ты бьёшь {m.acc}. -4", "\x1b[38;5;253m")
    c = render(game, w, h)
    c.flush()
    sys.stdout.write("\n")


def _reachable(d) -> set[tuple[int, int]]:
    seen = {d.start}
    queue = deque([d.start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen or not d.walkable(nx, ny):
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return seen


def selftest() -> None:
    rng = random.Random(1)
    for _ in range(80):
        w = rng.randint(38, 84)
        h = rng.randint(14, 26)
        depth = rng.randint(1, FINAL_FLOOR)
        d = build_dungeon(w, h, depth, rng)
        assert len(d.rooms) >= 2, "мало комнат"
        assert d.walkable(*d.start), "старт в стене"
        assert d.walkable(*d.exit), "выход в стене"
        reach = _reachable(d)
        assert d.exit in reach, "выход недостижим"
        for room in d.rooms:
            cx = room[0] + room[2] // 2
            cy = room[1] + room[3] // 2
            assert (cx, cy) in reach, "комната отрезана"

    keys = ["up", "down", "left", "right", ".", "g", "1", "2", ">"]
    for run in range(6):
        g = Game(random.Random(run))
        g.new_level(view=(72, 21))
        for _ in range(400):
            if g.state != "play":
                break
            g.try_action(rng.choice(keys))
        assert g.player.hp >= 0

    g = Game(random.Random(3))
    g.depth = FINAL_FLOOR
    g.new_level(view=(72, 21))
    g.monsters = [m for m in g.monsters if not m.boss]
    g.player.x, g.player.y = g.d.exit
    g.check_altar()
    assert g.state == "won", "алтарь не сработал"

    g = Game(random.Random(4))
    g.player.gain_xp(1000)
    assert g.player.level > 1

    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        setup_terminal()
        selftest()
        return
    if "--demo" in sys.argv:
        demo()
        return

    setup_terminal()
    inp = Input()
    try:
        enter_alt_screen()
        play(inp)
    except KeyboardInterrupt:
        pass
    finally:
        leave_alt_screen()


if __name__ == "__main__":
    main()
