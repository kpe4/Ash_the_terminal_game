# -*- coding: utf-8 -*-
"""Игрок, чудовища и предметы."""

from __future__ import annotations

BESTIARY = {
    "rat": dict(
        name="крыса", acc="крысу", verb="грызёт", ch="r",
        hp=4, atk=2, df=0, xp=3, shade=244,
    ),
    "bat": dict(
        name="летучая мышь", acc="летучую мышь", verb="царапает", ch="b",
        hp=3, atk=2, df=0, xp=3, shade=250, erratic=True,
    ),
    "goblin": dict(
        name="гоблин", acc="гоблина", verb="бьёт", ch="g",
        hp=7, atk=3, df=0, xp=6, shade=252,
    ),
    "skeleton": dict(
        name="скелет", acc="скелета", verb="рубит", ch="s",
        hp=10, atk=4, df=1, xp=9, shade=253,
    ),
    "orc": dict(
        name="орк", acc="орка", verb="ломает", ch="o",
        hp=14, atk=5, df=1, xp=13, shade=254,
    ),
    "wraith": dict(
        name="призрак", acc="призрака", verb="леденит", ch="w",
        hp=12, atk=5, df=2, xp=16, shade=255,
    ),
}


def monster_pool(depth: int) -> list[str]:
    if depth <= 1:
        return ["rat", "bat"]
    if depth == 2:
        return ["rat", "bat", "goblin"]
    if depth == 3:
        return ["bat", "goblin", "skeleton"]
    if depth == 4:
        return ["goblin", "skeleton", "orc"]
    if depth == 5:
        return ["skeleton", "orc", "wraith"]
    return ["orc", "skeleton", "wraith"]


class Monster:
    def __init__(self, kind: str, x: int, y: int, depth: int, boss: bool = False):
        data = BESTIARY.get(kind)
        if boss:
            self.kind = "guardian"
            self.name = "Пепельный страж"
            self.acc = "Пепельного стража"
            self.verb = "обжигает"
            self.ch = "Ω"
            self.hp = 42
            self.max_hp = 42
            self.atk = 8
            self.df = 2
            self.xp = 60
            self.shade = 255
            self.bold = True
            self.erratic = False
        else:
            assert data is not None
            self.kind = kind
            self.name = data["name"]
            self.acc = data["acc"]
            self.verb = data["verb"]
            self.ch = data["ch"]
            self.max_hp = data["hp"] + (depth - 1) * 2
            self.hp = self.max_hp
            self.atk = data["atk"] + (depth - 1) // 2
            self.df = data["df"] + (depth - 1) // 3
            self.xp = data["xp"] + depth
            self.shade = data["shade"]
            self.bold = False
            self.erratic = bool(data.get("erratic"))
        self.x = x
        self.y = y
        self.boss = boss
        self.aware = 0


class Player:
    def __init__(self) -> None:
        self.x = 1
        self.y = 1
        self.max_hp = 26
        self.hp = 26
        self.atk = 3
        self.defense = 0
        self.level = 1
        self.xp = 0
        self.next_xp = 12
        self.gold = 0
        self.potions = 2
        self.scrolls = 1
        self.turns = 0

    def gain_xp(self, amount: int) -> int:
        """Возвращает число полученных уровней."""
        self.xp += amount
        gained = 0
        while self.xp >= self.next_xp:
            self.xp -= self.next_xp
            self.level += 1
            gained += 1
            self.max_hp += 7
            self.hp = self.max_hp
            self.atk += 1
            if self.level % 2 == 0:
                self.defense += 1
            self.next_xp = int(self.next_xp * 1.55) + 6
        return gained


ITEMS = {
    "potion": dict(ch="!", name="зелье", shade=255),
    "scroll": dict(ch="?", name="свиток", shade=253),
    "sword": dict(ch=")", name="обломок клинка", shade=254),
    "armor": dict(ch="[", name="пластина брони", shade=254),
    "gold": dict(ch="$", name="золото", shade=251),
}
