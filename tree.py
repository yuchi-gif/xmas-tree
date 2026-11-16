#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""电子圣诞树 · 终端版

运行：python tree.py
退出：Ctrl+C
只看一帧：python tree.py --once

只用标准库。用 24 位真彩色 + 半格字符（▀）把终端当作像素屏，
绘制旋转的灯串、闪烁灯珠、星芒与飘雪。
"""

import colorsys
import math
import os
import random
import shutil
import sys
import time

TAU = math.pi * 2

STRAND_HUES = [0.122, 0.422, 0.128, 0.544, 0.933, 0.439, 0.111, 0.483, 0.800]
ACCENT_HUES = [0.933, 0.544, 0.122, 0.800, 0.022]
ORNAMENT_HUES = [0.985, 0.108, 0.544, 0.917, 0.130, 0.755]

RAD = 0.40
BOTTOM = -0.53
HEIGHT = 1.06
CAM_Z = 3.0
FOCAL = 2.6
TEXT_ROWS = 3
MAX_FPS = 24


def enable_ansi():
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def hsv(hue, sat, val):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, max(0.0, min(1.0, sat)), max(0.0, min(1.0, val)))
    return r * 255.0, g * 255.0, b * 255.0



def build_tree():
    points = []
    strands, turns, per = 7, 5.0, 44

    for s in range(strands):
        for i in range(per):
            t = i / (per - 1)
            radius = RAD * (1.0 - t) ** 0.94 * (0.95 + 0.05 * math.sin(t * math.pi))
            ang = s * (TAU / strands) + t * turns * TAU
            hue = STRAND_HUES[s] + t * 0.016
            accent = i % 26 == 0
            points.append(
                {
                    "x": math.cos(ang) * radius,
                    "y": BOTTOM + t * HEIGHT,
                    "z": math.sin(ang) * radius,
                    "hue": ACCENT_HUES[(i // 26 + s) % len(ACCENT_HUES)] if accent else hue,
                    "size": 1.05 if accent else 0.58,
                    "phase": random.uniform(0, TAU),
                    "speed": random.uniform(1.1, 2.7),
                    "accent": accent,
                    "strand": s,
                    "idx": i,
                    "bulb": i % 5 == 0,
                }
            )

    rng = random
    for _ in range(240):
        t = rng.random() ** 0.82
        radius = RAD * (1.0 - t) ** 0.94 * rng.uniform(0.42, 1.0)
        ang = rng.uniform(0, TAU)
        points.append(
            {
                "x": math.cos(ang) * radius,
                "y": BOTTOM + t * HEIGHT,
                "z": math.sin(ang) * radius,
                "hue": rng.uniform(0.395, 0.478),
                "size": 0.22,
                "phase": rng.uniform(0, TAU),
                "speed": rng.uniform(0.6, 1.8),
                "accent": False,
                "bulb": False,
                "strand": None,
                "idx": -1,
            }
        )

    for _ in range(32):
        t = rng.random() ** 0.72
        radius = RAD * (1.0 - t) ** 0.94 * rng.uniform(0.9, 1.04)
        ang = rng.uniform(0, TAU)
        points.append(
            {
                "x": math.cos(ang) * radius,
                "y": BOTTOM + t * HEIGHT,
                "z": math.sin(ang) * radius,
                "hue": rng.choice(ORNAMENT_HUES),
                "size": 1.5,
                "phase": rng.uniform(0, TAU),
                "speed": rng.uniform(0.8, 2.0),
                "accent": False,
                "bulb": False,
            }
        )

    return points


class Screen:
    def __init__(self, term_cols, term_rows):
        self.resize(term_cols, term_rows)

    def resize(self, term_cols, term_rows):
        import random

        self.cols = max(28, min(term_cols, 110))
        self.rows = max(12, term_rows - TEXT_ROWS)
        self.w = self.cols
        self.h = self.rows * 2
        self.buf = [0.0] * (self.w * self.h * 3)
        self.scale = min(self.h * 0.72, self.w * 1.05)
        self.cx = self.w / 2.0
        self.cy = self.h * 0.46
        self.snow = [
            {
                "x": random.uniform(0, self.w),
                "y": random.uniform(0, self.h),
                "v": random.uniform(0.6, 2.1),
                "phase": random.uniform(0, TAU),
                "speed": random.uniform(0.4, 1.2),
                "a": random.uniform(0.07, 0.34),
            }
            for _ in range(max(24, int(self.cols * 0.9)))
        ]

    def clear_background(self):
        buf = self.buf
        w = self.w
        for y in range(self.h):
            k = y / max(1, self.h - 1)
            r = 6.0 - 4.0 * k
            g = 18.0 - 12.0 * k
            b = 26.0 - 18.0 * k
            base = y * w * 3
            for x in range(w):
                i = base + x * 3
                dx = (x - self.cx) / (self.scale * 0.95)
                dy = (y - self.cy) / (self.scale * 1.05)
                glow = max(0.0, 1.0 - math.hypot(dx, dy) * 1.15)
                buf[i] = r + 10.0 * glow
                buf[i + 1] = g + 30.0 * glow
                buf[i + 2] = b + 32.0 * glow

    def add(self, x, y, r, g, b):
        ix = int(x)
        iy = int(y)
        if ix < 0 or iy < 0 or ix >= self.w - 1 or iy >= self.h - 1:
            return
        fx = x - ix
        fy = y - iy
        w = self.w
        buf = self.buf
        corners = (
            (ix, iy, (1 - fx) * (1 - fy)),
            (ix + 1, iy, fx * (1 - fy)),
            (ix, iy + 1, (1 - fx) * fy),
            (ix + 1, iy + 1, fx * fy),
        )
        for px, py, weight in corners:
            idx = (py * w + px) * 3
            buf[idx] += r * weight
            buf[idx + 1] += g * weight
            buf[idx + 2] += b * weight


def project(x, y, z, rot, cos_t, sin_t, screen):
    cos_y = math.cos(rot)
    sin_y = math.sin(rot)
    x1 = x * cos_y + z * sin_y
    z1 = z * cos_y - x * sin_y
    y2 = y * cos_t - z1 * sin_t
    z2 = y * sin_t + z1 * cos_t
    k = FOCAL / (CAM_Z - z2) * screen.scale
    return screen.cx + x1 * k, screen.cy - y2 * k, k, z2


def render(points, screen, t, rot, tilt, snow_dt):
    screen.clear_background()
    w = screen.w
    h = screen.h

    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)

    last_strand = None
    last_pos = None
    for p in points:
        sx, sy, k, depth = project(p["x"], p["y"], p["z"], rot, cos_t, sin_t, screen)
        strand = p.get("strand")
        if strand is not None:
            if last_strand == strand and last_pos is not None:
                seg = math.hypot(sx - last_pos[0], sy - last_pos[1])
                steps = max(1, int(seg / 0.6))
                lr, lg, lb = hsv(p["hue"], 0.8, 0.62)
                for j in range(1, steps):
                    f = j / steps
                    screen.add(
                        last_pos[0] + (sx - last_pos[0]) * f,
                        last_pos[1] + (sy - last_pos[1]) * f,
                        lr * 0.065,
                        lg * 0.065,
                        lb * 0.065,
                    )
            last_strand = strand
            last_pos = (sx, sy)
        else:
            last_strand = None
            last_pos = None
        twinkle = 0.62 + 0.38 * math.sin(t * p["speed"] + p["phase"])
        size = p["size"]
        if p["bulb"]:
            size *= 1.45
        size *= (k / screen.scale) * 2.6
        size = max(0.6, min(3.0, size))

        sat = 0.42 if p["size"] < 0.4 else 0.64
        val = (0.30 if p["size"] < 0.4 else 0.52) * twinkle
        if p["accent"]:
            sat = 0.96
            val = 1.0
        r, g, b = hsv(p["hue"], sat, val)

        fade = 0.34 + 0.66 * max(0.0, min(1.0, (depth + 0.45) / 0.9))
        gain = (1.35 if p["bulb"] else 0.72) * size * fade
        screen.add(sx, sy, r * gain, g * gain, b * gain)

        if p["bulb"] or p["accent"]:
            glow = gain * 0.22
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                screen.add(sx + dx, sy + dy, r * glow, g * glow, b * glow)
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                screen.add(sx + dx, sy + dy, r * glow * 0.35, g * glow * 0.35, b * glow * 0.35)

    top_y = BOTTOM + HEIGHT + 0.055
    sx, sy, _, _ = project(0, top_y, 0, rot, cos_t, sin_t, screen)
    pulse = 0.82 + 0.18 * math.sin(t * 2.4)
    for i in range(-3, 4):
        f = pulse * (1.0 - abs(i) / 4.2)
        screen.add(sx + i, sy, 255 * f, 236 * f, 180 * f)
        screen.add(sx, sy + i, 255 * f, 236 * f, 180 * f)
    screen.add(sx, sy, 255, 250, 225)

    for f in screen.snow:
        f["y"] += f["v"] * snow_dt * 24.0
        f["x"] += math.sin(t * f["speed"] + f["phase"]) * 0.12
        if f["y"] > h - 1:
            f["y"] = -1
            f["x"] = (f["x"] + w * 0.37) % w
        if f["x"] < 0:
            f["x"] += w
        if f["x"] >= w:
            f["x"] -= w
        screen.add(f["x"], f["y"], 210 * f["a"], 232 * f["a"], 255 * f["a"])

    return to_frame(screen)


def to_frame(screen):
    w = screen.w
    h = screen.h
    buf = screen.buf
    parts = ["\x1b[H"]
    for row in range(h // 2):
        top_ids = [0] * w
        bot_ids = [0] * w
        y0 = row * 2
        y1 = y0 + 1
        for x in range(w):
            i0 = (y0 * w + x) * 3
            i1 = (y1 * w + x) * 3
            r = min(255, int(buf[i0]))
            g = min(255, int(buf[i0 + 1]))
            b = min(255, int(buf[i0 + 2]))
            top_ids[x] = (r << 16) | (g << 8) | b
            r = min(255, int(buf[i1]))
            g = min(255, int(buf[i1 + 1]))
            b = min(255, int(buf[i1 + 2]))
            bot_ids[x] = (r << 16) | (g << 8) | b

        line = []
        i = 0
        while i < w:
            top = top_ids[i]
            bot = bot_ids[i]
            j = i + 1
            while j < w and top_ids[j] == top and bot_ids[j] == bot:
                j += 1
            line.append(
                "\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm%s"
                % (
                    top >> 16,
                    (top >> 8) & 255,
                    top & 255,
                    bot >> 16,
                    (bot >> 8) & 255,
                    bot & 255,
                    "▀" * (j - i),
                )
            )
            i = j
        parts.append("".join(line) + "\x1b[0m")
    return "\r\n".join(parts)


def centered(text, width):
    pad = max(0, (width - len(text)) // 2)
    return " " * pad + text


def main():
    once = "--once" in sys.argv
    enable_ansi()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    points = build_tree()
    term = shutil.get_terminal_size((90, 34))
    screen = Screen(term.columns, term.lines)

    gold = "\x1b[38;2;255;208;132m"
    dim = "\x1b[38;2;150;186;190m"
    reset = "\x1b[0m"

    if not once:
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        sys.stdout.flush()

    start = time.monotonic()
    last = start
    frame_budget = 1.0 / MAX_FPS

    try:
        while True:
            now = time.monotonic()
            t = now - start
            term = shutil.get_terminal_size((90, 34))
            if term.columns != screen.cols or max(12, term.lines - TEXT_ROWS) != screen.rows:
                screen.resize(term.columns, term.lines)
                if not once:
                    sys.stdout.write("\x1b[2J")
            dt = max(0.0, min(now - last, 0.1))
            last = now

            rot = t * 0.55 if not once else 2.1
            frame = render(points, screen, t, rot, 0.10, dt)

            footer = (
                "\r\n"
                + gold
                + centered("M E R R Y   C H R I S T M A S", screen.w)
                + reset
                + "\r\n"
                + dim
                + centered("圣 诞 快 乐 · 平 安 喜 乐", screen.w)
                + reset
            )

            sys.stdout.write(frame + footer)
            if once:
                sys.stdout.write("\r\n")
                break
            sys.stdout.flush()

            elapsed = time.monotonic() - now
            if elapsed < frame_budget:
                time.sleep(frame_budget - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        if not once:
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
