# -*- coding: utf-8 -*-
"""Правила игры ПЕПЕЛ: ходы, бой, этажи, предметы."""

from __future__ import annotations

import random
from collections import deque

from .dungeon import (
    ALTAR,
    FINAL_FLOOR,
    FLOOR,
    STAIRS,
    WALL,
    build_dungeon,
    compute_fov,
    manhattan,
)
from .entities import ITEMS, Monster, Player, monster_pool
from .paint import layout
from .screen import MIN_H, MIN_W, Pal, term_size

DIRS = {
    "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
    "w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0),
    "k": (0, -1), "j": (0, 1), "h": (-1, 0), "l": (1, 0),
}


class Game:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.player = Player()
        self.depth = 1
        self.turn = 0
        self.state = "play"  # play | dead | won | left
        self.log: deque[tuple[str, str]] = deque(maxlen=8)
        self.d = None
        self.monsters: list[Monster] = []
        self.items: dict[tuple[int, int], dict] = {}
        self.fx: dict[tuple[int, int], str] = {}
        self.visible: set[tuple[int, int]] = set()
        self.explored: set[tuple[int, int]] = set()
        self.new_level()
        self.msg("Ты входишь в шахту. Пепел хрустит под ногами.", Pal.light)
        self.msg("Спустись на семь этажей и найди алтарь.", Pal.dim)

    # ───────────────────────────── уровень ─────────────────────────────

    def new_level(self, view: tuple[int, int] | None = None) -> None:
        if view is None:
            w, h = term_size()
            if w < MIN_W or h < MIN_H:
                w, h = 100, 30
            lay = layout(w, h - 1)
            view = (lay["map_w"], lay["map_h"])
        dw = max(38, min(view[0], 84))
        dh = max(14, min(view[1], 26))
        self.d = build_dungeon(dw, dh, self.depth, self.rng)
        self.player.x, self.player.y = self.d.start
        self.monsters = []
        self.items = {}
        self.fx = {}
        self.explored = set()
        self.visible = set()
        self.spawn_entities()
        self.update_fov()

    def free_tiles(self) -> list[tuple[int, int]]:
        assert self.d is not None
        return [
            (x, y)
            for y in range(self.d.h)
            for x in range(self.d.w)
            if self.d.tiles[y][x] == FLOOR
            and (x, y) != self.d.start
            and (x, y) != self.d.exit
            and manhattan((x, y), self.d.start) >= 3
        ]

    def spawn_entities(self) -> None:
        assert self.d is not None
        rng = self.rng
        free = self.free_tiles()
        rng.shuffle(free)

        def take(near: tuple[int, int] | None = None, min_dist: int = 0):
            nonlocal free
            if near is not None:
                free.sort(key=lambda p: manhattan(p, near))
            while free:
                pos = free.pop(0 if near is not None else -1)
                if manhattan(pos, self.d.start) >= min_dist:
                    return pos
            return None

        # предметы
        potions = rng.randint(1, 2)
        if self.depth >= 4:
            potions += 1
        if self.depth >= 6:
            potions += 1
        for _ in range(potions):
            pos = take(min_dist=3)
            if pos:
                self.items[pos] = {"kind": "potion"}
        if rng.random() < (0.55 + self.depth * 0.04):
            pos = take(min_dist=3)
            if pos:
                self.items[pos] = {"kind": "scroll"}
        if rng.random() < 0.45:
            pos = take(min_dist=4)
            if pos:
                self.items[pos] = {"kind": "sword"}
        if rng.random() < 0.4:
            pos = take(min_dist=4)
            if pos:
                self.items[pos] = {"kind": "armor"}
        for _ in range(rng.randint(2, 4)):
            pos = take(min_dist=2)
            if pos:
                self.items[pos] = {
                    "kind": "gold",
                    "amount": rng.randint(4, 12) + self.depth * 3,
                }

        # чудовища
        count = 5 if self.depth >= FINAL_FLOOR else min(13, 3 + self.depth)
        pool = monster_pool(self.depth)
        for _ in range(count):
            pos = take(min_dist=7)
            if not pos:
                continue
            kind = rng.choice(pool)
            self.monsters.append(Monster(kind, pos[0], pos[1], self.depth))

        # страж последнего этажа
        if self.depth >= FINAL_FLOOR:
            pos = self.near_exit_tile()
            if pos is None:
                spots = [
                    (x, y)
                    for y in range(self.d.h)
                    for x in range(self.d.w)
                    if self.d.tiles[y][x] == FLOOR
                    and (x, y) != self.d.start
                    and self.monster_at(x, y) is None
                ]
                if spots:
                    pos = max(spots, key=lambda p: manhattan(p, self.d.exit))
            if pos:
                self.monsters.append(
                    Monster("guardian", pos[0], pos[1], self.depth, boss=True)
                )

    def near_exit_tile(self) -> tuple[int, int] | None:
        assert self.d is not None
        candidates = []
        ex, ey = self.d.exit
        for y in range(max(0, ey - 3), min(self.d.h, ey + 4)):
            for x in range(max(0, ex - 3), min(self.d.w, ex + 4)):
                if (x, y) == self.d.exit:
                    continue
                if self.d.tiles[y][x] != FLOOR:
                    continue
                if (x, y) == self.d.start:
                    continue
                if any((m.x, m.y) == (x, y) for m in self.monsters):
                    continue
                if (x, y) in self.items:
                    continue
                candidates.append((x, y))
        if not candidates:
            return None
        candidates.sort(key=lambda p: manhattan(p, self.d.exit))
        return candidates[0]

    # ───────────────────────────── служебное ─────────────────────────────

    def msg(self, text: str, color: str = Pal.mid) -> None:
        self.log.append((text, color))

    def update_fov(self) -> None:
        assert self.d is not None
        self.visible = compute_fov(self.d, self.player.x, self.player.y)
        self.explored.update(self.visible)

    def monster_at(self, x: int, y: int) -> Monster | None:
        for m in self.monsters:
            if m.x == x and m.y == y:
                return m
        return None

    def guardian_alive(self) -> bool:
        return any(m.boss for m in self.monsters)

    def tile(self, x: int, y: int) -> int:
        assert self.d is not None
        return self.d.tiles[y][x]

    # ───────────────────────────── ходы ─────────────────────────────

    def try_action(self, key: str) -> bool:
        if self.state != "play":
            return False
        self.fx.clear()
        p = self.player
        consumed = False

        if key in DIRS:
            dx, dy = DIRS[key]
            nx, ny = p.x + dx, p.y + dy
            target = self.monster_at(nx, ny)
            if target is not None:
                self.player_attack(target)
                consumed = True
            elif self.d is not None and self.d.walkable(nx, ny):
                p.x, p.y = nx, ny
                self.auto_pickup()
                consumed = True
                if self.tile(p.x, p.y) == ALTAR:
                    self.check_altar()
                    if self.state != "play":
                        return True
            # стена — просто ничего не происходит

        elif key == "1":
            if p.potions <= 0:
                self.msg("Зелий нет.", Pal.dim)
            elif p.hp >= p.max_hp:
                self.msg("Раны уже затянулись.", Pal.dim)
            else:
                p.potions -= 1
                heal = min(14, p.max_hp - p.hp)
                p.hp += heal
                self.msg(f"Ты пьёшь зелье. +{heal} HP.", Pal.bright)
                consumed = True

        elif key == "2":
            if p.scrolls <= 0:
                self.msg("Свитков нет.", Pal.dim)
            else:
                p.scrolls -= 1
                self.explored.update(
                    (x, y)
                    for y in range(self.d.h)
                    for x in range(self.d.w)
                    if self.d.tiles[y][x] != WALL
                )
                self.msg("Свиток вспыхивает. Весь этаж как на ладони.", Pal.bright)
                consumed = True

        elif key == "g":
            self.pick_up()

        elif key in (".", " ", "5"):
            consumed = True

        elif key == ">":
            if self.tile(p.x, p.y) == STAIRS:
                self.descend()
                return True
            self.msg("Здесь нет лестницы.", Pal.dim)

        if consumed:
            self.end_turn()
        return consumed

    def auto_pickup(self) -> None:
        p = self.player
        item = self.items.get((p.x, p.y))
        if item and item["kind"] == "gold":
            del self.items[(p.x, p.y)]
            p.gold += item["amount"]
            self.msg(f"Ты поднимаешь {item['amount']} золота.", Pal.light)

    def pick_up(self) -> None:
        p = self.player
        item = self.items.get((p.x, p.y))
        if not item:
            self.msg("Здесь нечего поднимать.", Pal.dim)
            return
        kind = item["kind"]
        if kind == "potion":
            p.potions += 1
            self.msg("Ты поднимаешь зелье.", Pal.light)
        elif kind == "scroll":
            p.scrolls += 1
            self.msg("Ты поднимаешь свиток.", Pal.light)
        elif kind == "sword":
            p.atk += 1
            self.msg("Обломок клинка врастает в руку. Атака +1.", Pal.bright)
        elif kind == "armor":
            p.defense += 1
            self.msg("Пластина холодит грудь. Защита +1.", Pal.bright)
        elif kind == "gold":
            p.gold += item["amount"]
            self.msg(f"Ты поднимаешь {item['amount']} золота.", Pal.light)
        del self.items[(p.x, p.y)]

    def descend(self) -> None:
        p = self.player
        if self.depth >= FINAL_FLOOR:
            self.msg("Глубже только пепел.", Pal.dim)
            return
        self.depth += 1
        self.msg(f"Ты спускаешься на этаж {self.depth}.", Pal.bright)
        if p.hp < p.max_hp:
            p.hp = min(p.max_hp, p.hp + 4)
        self.new_level()
        if self.depth >= FINAL_FLOOR:
            self.msg("Внизу что-то дышит. Алтарь ждёт.", Pal.white)

    def check_altar(self) -> None:
        if self.guardian_alive():
            self.msg("Алтарь холоден. Страж ещё дышит.", Pal.dim)
            return
        self.state = "won"
        self.msg("Ты зажигаешь пепельный алтарь.", Pal.white)

    # ───────────────────────────── бой ─────────────────────────────

    def player_attack(self, m: Monster) -> None:
        p = self.player
        dmg = max(1, p.atk + self.rng.randint(0, 2) - m.df)
        m.hp -= dmg
        self.fx[(m.x, m.y)] = f"-{dmg}"
        if m.hp <= 0:
            if m in self.monsters:
                self.monsters.remove(m)
            levels = p.gain_xp(m.xp)
            self.msg(f"{m.name.capitalize()} рассыпается в прах. +{m.xp} опыта.", Pal.bright)
            if m.boss:
                self.msg("Страж падает. Алтарь вспыхивает.", Pal.white)
            if levels:
                self.msg(f"Пепел оседает на плечах. Уровень {p.level}.", Pal.white)
        else:
            self.msg(f"Ты бьёшь {m.acc}. -{dmg}", Pal.light)

    def monster_attack(self, m: Monster) -> None:
        p = self.player
        dmg = max(1, m.atk + self.rng.randint(0, 2) - p.defense)
        p.hp -= dmg
        self.fx[(p.x, p.y)] = f"-{dmg}"
        self.msg(f"{m.name.capitalize()} {m.verb} тебя. -{dmg}", Pal.light)
        if p.hp <= 0:
            p.hp = 0
            self.state = "dead"
            self.msg("Тьма смыкается.", Pal.white)

    def end_turn(self) -> None:
        self.update_fov()
        self.monsters_act()
        if self.state != "play":
            return
        self.turn += 1
        self.player.turns += 1
        self.update_fov()

    # ───────────────────────────── чудовища ─────────────────────────────

    def can_monster_move(self, m: Monster, x: int, y: int) -> bool:
        if self.d is None or not self.d.walkable(x, y):
            return False
        if (x, y) == (self.player.x, self.player.y):
            return False
        return self.monster_at(x, y) is None

    def monsters_act(self) -> None:
        p = self.player
        for m in list(self.monsters):
            if self.state != "play":
                return
            if m.hp <= 0:
                continue
            if manhattan((m.x, m.y), (p.x, p.y)) == 1:
                self.monster_attack(m)
                continue
            if (m.x, m.y) in self.visible:
                m.aware = 8
            if m.aware <= 0:
                if self.rng.random() < 0.2:
                    self.random_step(m)
                continue
            m.aware -= 1
            if m.erratic and self.rng.random() < 0.45:
                self.random_step(m)
            else:
                self.chase_step(m)

    def random_step(self, m: Monster) -> None:
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        self.rng.shuffle(dirs)
        for dx, dy in dirs:
            if self.can_monster_move(m, m.x + dx, m.y + dy):
                m.x += dx
                m.y += dy
                return

    def chase_step(self, m: Monster) -> None:
        p = self.player
        dx = (p.x > m.x) - (p.x < m.x)
        dy = (p.y > m.y) - (p.y < m.y)
        options = []
        if abs(p.x - m.x) >= abs(p.y - m.y):
            options = [(dx, 0), (0, dy)]
        else:
            options = [(0, dy), (dx, 0)]
        for ox, oy in options:
            if ox == 0 and oy == 0:
                continue
            if self.can_monster_move(m, m.x + ox, m.y + oy):
                m.x += ox
                m.y += oy
                return
        best = None
        best_dist = manhattan((m.x, m.y), (p.x, p.y))
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = m.x + ox, m.y + oy
            if not self.can_monster_move(m, nx, ny):
                continue
            dist = manhattan((nx, ny), (p.x, p.y))
            if dist < best_dist:
                best_dist = dist
                best = (nx, ny)
        if best:
            m.x, m.y = best
