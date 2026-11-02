# -*- coding: utf-8 -*-
"""Генерация подземелья, полоса видимости, мелкие утилиты."""

from __future__ import annotations

import random

WALL, FLOOR, STAIRS, ALTAR = 0, 1, 2, 3
FINAL_FLOOR = 7


def wrap_text(text: str, width: int) -> list[str]:
    if width <= 0:
        return [""]
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        while len(word) > width:
            lines.append(word[:width])
            word = word[width:]
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Dungeon:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.tiles = [[WALL] * w for _ in range(h)]
        self.rooms: list[tuple[int, int, int, int]] = []
        self.start = (1, 1)
        self.exit = (1, 1)
        self.exit_tile = STAIRS

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def walkable(self, x: int, y: int) -> bool:
        return self.inside(x, y) and self.tiles[y][x] != WALL


def _overlaps(a, b, pad: int = 1) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax - pad < bx + bw
        and bx - pad < ax + aw
        and ay - pad < by + bh
        and by - pad < ay + ah
    )


def _center(room) -> tuple[int, int]:
    x, y, w, h = room
    return x + w // 2, y + h // 2


def build_dungeon(w: int, h: int, depth: int, rng: random.Random) -> Dungeon:
    d = Dungeon(w, h)
    target = max(6, min(16, (w * h) // 75))
    attempts = 0
    while len(d.rooms) < target and attempts < 600:
        attempts += 1
        rw = rng.randint(4, min(11, w - 4))
        rh = rng.randint(3, min(6, h - 4))
        if rw < 4 or rh < 3:
            continue
        rx = rng.randint(1, w - rw - 2)
        ry = rng.randint(1, h - rh - 2)
        room = (rx, ry, rw, rh)
        if any(_overlaps(room, other) for other in d.rooms):
            continue
        d.rooms.append(room)
        for yy in range(ry, ry + rh):
            for xx in range(rx, rx + rw):
                d.tiles[yy][xx] = FLOOR

    # на всякий случай — хотя бы две комнаты
    while len(d.rooms) < 2:
        rw, rh = 5, 4
        rx, ry = 2 + len(d.rooms) * 7, 2
        if rx + rw + 1 >= w:
            rx = 2
        room = (rx, ry, rw, rh)
        d.rooms.append(room)
        for yy in range(ry, ry + rh):
            for xx in range(rx, rx + rw):
                if d.inside(xx, yy):
                    d.tiles[yy][xx] = FLOOR

    def carve_h(x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if d.inside(x, y) and d.tiles[y][x] == WALL:
                d.tiles[y][x] = FLOOR

    def carve_v(y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if d.inside(x, y) and d.tiles[y][x] == WALL:
                d.tiles[y][x] = FLOOR

    def connect(i: int, j: int) -> None:
        x1, y1 = _center(d.rooms[i])
        x2, y2 = _center(d.rooms[j])
        if rng.random() < 0.5:
            carve_h(x1, x2, y1)
            carve_v(y1, y2, x2)
        else:
            carve_v(y1, y2, x1)
            carve_h(x1, x2, y2)

    for i in range(1, len(d.rooms)):
        connect(i - 1, i)
    for i in range(len(d.rooms) - 2):
        if rng.random() < 0.3:
            connect(i, i + 2)

    d.start = _center(d.rooms[0])
    sx, sy = d.start
    d.tiles[sy][sx] = FLOOR

    far = max(range(1, len(d.rooms)), key=lambda i: manhattan(_center(d.rooms[i]), d.start))
    ex, ey = _center(d.rooms[far])
    if (ex, ey) == d.start:
        free = [
            (x, y)
            for y in range(h)
            for x in range(w)
            if d.tiles[y][x] == FLOOR and (x, y) != d.start
        ]
        if free:
            ex, ey = max(free, key=lambda p: manhattan(p, d.start))
    d.exit = (ex, ey)
    d.exit_tile = ALTAR if depth >= FINAL_FLOOR else STAIRS
    d.tiles[ey][ex] = d.exit_tile
    return d


def line_of_sight(tiles, w: int, h: int, x0: int, y0: int, x1: int, y1: int) -> bool:
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while (x, y) != (x1, y1):
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
        if (x, y) == (x1, y1):
            break
        if tiles[y][x] == WALL:
            return False
    return True


def compute_fov(d: Dungeon, px: int, py: int, radius: float = 9.0) -> set[tuple[int, int]]:
    visible: set[tuple[int, int]] = {(px, py)}
    r = int(radius) + 1
    for y in range(max(0, py - r), min(d.h, py + r + 1)):
        for x in range(max(0, px - r), min(d.w, px + r + 1)):
            if (x - px) ** 2 + (y - py) ** 2 > radius * radius:
                continue
            if line_of_sight(d.tiles, d.w, d.h, px, py, x, y):
                visible.add((x, y))
    return visible
