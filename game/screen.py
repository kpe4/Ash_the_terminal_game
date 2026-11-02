# -*- coding: utf-8 -*-
"""Экран, палитра и ввод для игры ПЕПЕЛ."""

from __future__ import annotations

import os
import shutil
import sys
import time

RESET = "\x1b[0m"
MIN_W, MIN_H = 74, 24


def fg(n: int, bold: bool = False) -> str:
    if bold:
        return f"\x1b[1;38;5;{n}m"
    return f"\x1b[38;5;{n}m"


class Pal:
    """Только оттенки серого — ничего лишнего."""
    faint = fg(235)
    dark = fg(238)
    dim = fg(241)
    mid = fg(246)
    light = fg(250)
    bright = fg(253)
    white = fg(255, True)
    ember = fg(255)


def term_size() -> tuple[int, int]:
    try:
        s = shutil.get_terminal_size()
        return s.columns, s.lines
    except Exception:
        return 100, 30


def setup_terminal() -> None:
    if os.name == "nt":
        try:
            import ctypes

            kernel = ctypes.windll.kernel32
            try:
                kernel.SetConsoleTitleW("ПЕПЕЛ — монохромный рогалик")
            except Exception:
                pass
            try:
                kernel.SetConsoleOutputCP(65001)
                kernel.SetConsoleCP(65001)
            except Exception:
                pass
            handle = kernel.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def enter_alt_screen() -> None:
    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    sys.stdout.flush()


def leave_alt_screen() -> None:
    sys.stdout.write(f"{RESET}\x1b[?25h\x1b[?1049l")
    sys.stdout.flush()


class Canvas:
    """Кадровый буфер из символов и цветов."""

    def __init__(self, w: int, h: int):
        self.w = max(1, w)
        self.h = max(1, h)
        self.buf = [[(" ", "") for _ in range(self.w)] for _ in range(self.h)]

    def put(self, x: int, y: int, text: str, color: str = "") -> None:
        if y < 0 or y >= self.h:
            return
        for i, ch in enumerate(text):
            xx = x + i
            if 0 <= xx < self.w:
                self.buf[y][xx] = (ch, color)

    def put_right(self, x_right: int, y: int, text: str, color: str = "") -> None:
        self.put(x_right - len(text) + 1, y, text, color)

    def fill(self, x: int, y: int, w: int, h: int, ch: str = " ", color: str = "") -> None:
        y0, y1 = max(0, y), min(self.h, y + h)
        x0, x1 = max(0, x), min(self.w, x + w)
        for yy in range(y0, y1):
            row = self.buf[yy]
            for xx in range(x0, x1):
                row[xx] = (ch, color)

    def frame(self, x: int, y: int, w: int, h: int, color: str) -> None:
        if w < 2 or h < 2:
            return
        self.put(x, y, "┌" + "─" * (w - 2) + "┐", color)
        self.put(x, y + h - 1, "└" + "─" * (w - 2) + "┘", color)
        for yy in range(y + 1, y + h - 1):
            self.put(x, yy, "│", color)
            self.put(x + w - 1, yy, "│", color)

    def center(self, y: int, text: str, color: str = "") -> None:
        self.put((self.w - len(text)) // 2, y, text, color)

    def flush(self, clear: bool = False) -> None:
        out = []
        if clear:
            out.append("\x1b[2J")
        out.append("\x1b[H")
        for y in range(self.h):
            row = self.buf[y]
            if y == self.h - 1:
                row = row[:-1]  # нижний правый угол не должен прокручивать экран
            parts: list[str] = []
            current = None
            for ch, color in row:
                if color != current:
                    parts.append(RESET + color if color else RESET)
                    current = color
                parts.append(ch)
            out.append("".join(parts) + RESET)
            if y != self.h - 1:
                out.append("\r\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()


class Input:
    """Клавиатура: стрелки, WASD, русская раскладка, vi-клавиши."""

    RU = {
        "ц": "w", "ф": "a", "ы": "s", "в": "d", "й": "q",
        "п": "g", "ю": ">", "ж": ";", "э": "'", "х": "[",
        "ъ": "]", "б": ",", "ё": "`",
    }

    def __init__(self) -> None:
        self.win = os.name == "nt"
        if self.win:
            import msvcrt
            self.msvcrt = msvcrt

    @classmethod
    def normalize(cls, ch: str) -> str:
        if not ch:
            return ""
        low = ch.lower()
        if low in cls.RU:
            return cls.RU[low]
        if len(low) == 1:
            return low
        return ""

    def _read_win(self) -> str:
        ch = self.msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            code = self.msvcrt.getwch()
            return {
                "H": "up", "P": "down", "K": "left", "M": "right",
                "I": "pgup", "Q": "pgdn", "G": "home", "O": "end",
            }.get(code, "")
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x1b":
            return "esc"
        if ch == "\x08":
            return "backspace"
        return self.normalize(ch)

    def _read_posix(self) -> str:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = ""
                for _ in range(2):
                    if select.select([sys.stdin], [], [], 0.03)[0]:
                        seq += sys.stdin.read(1)
                    else:
                        break
                return {"[A": "up", "[B": "down", "[C": "right", "[D": "left"}.get(seq, "esc")
            if ch in ("\r", "\n"):
                return "enter"
            if ch == "\x03":
                raise KeyboardInterrupt
            return self.normalize(ch)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def wait(self) -> str:
        if self.win:
            return self._read_win()
        return self._read_posix()

    def poll(self, timeout: float = 0.0) -> str | None:
        if self.win:
            end = time.time() + timeout
            while True:
                if self.msvcrt.kbhit():
                    return self._read_win()
                if time.time() >= end:
                    return None
                time.sleep(0.008)
        import select

        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        return self._read_posix() if ready else None
