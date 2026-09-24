"""Pack chip outlines onto as few boards as possible.

Raster nesting: each outline (grown by half the gap) is rasterized onto a grid,
and candidate spots are found with an FFT cross-correlation against the board's
occupancy. Parts go largest-first, first-fit across boards, bottom-left within a
board. Several part orderings are tried and the best result is kept.
Uses true shapes, not bounding boxes, so an L-shaped part can tuck into
another's notch.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import numpy as np
import shapely
from scipy.signal import correlate
from shapely import affinity
from shapely.geometry import Polygon


@dataclass
class Settings:
    # Inches.
    board_w: float = 12.0
    board_h: float = 12.0
    margin: float = 0.2      # board edge to part edge
    gap: float = 0.125       # part edge to part edge; must exceed kerf
    rotation_step: float = 90.0
    res: float = 1 / 32      # grid cell size; smaller packs tighter, runs slower
    tries: int = 6
    seed: int = 0


@dataclass
class Placed:
    name: str
    geom: Polygon            # in board coordinates, inches, origin at bottom-left
    angle: float


@dataclass
class Board:
    parts: list = field(default_factory=list)

    def used_area(self):
        return sum(p.geom.area for p in self.parts)


class NestError(Exception):
    pass


class _Variant:
    """One rotation of one part, rasterized."""

    def __init__(self, geom, angle, s):
        self.angle = angle
        self.geom = affinity.rotate(geom, angle, origin=(0, 0))
        # Rasterize the outer outline only: dropping small parts into another
        # part's holes risks them shifting once that hole is cut. Grow it so any
        # cell the gap-padded outline touches gets marked.
        pad = s.gap / 2 + s.res * math.sqrt(2) / 2
        g = Polygon(self.geom.exterior).buffer(pad, quad_segs=8)
        x0, y0, x1, y1 = g.bounds
        nx, ny = math.ceil((x1 - x0) / s.res), math.ceil((y1 - y0) / s.res)
        xs = x0 + (np.arange(nx) + 0.5) * s.res
        ys = y0 + (np.arange(ny) + 0.5) * s.res
        X, Y = np.meshgrid(xs, ys)
        self.mask = shapely.contains_xy(g, X, Y).astype(np.float32)
        self.origin = (x0, y0)


class _Sheet:
    def __init__(self, s):
        self.s = s
        self.ny, self.nx = int(s.board_h // s.res), int(s.board_w // s.res)
        self.occ = np.zeros((self.ny, self.nx), np.float32)
        edge = max(0, math.ceil((s.margin - s.gap / 2) / s.res))
        if edge:
            self.occ[:edge, :] = self.occ[-edge:, :] = 1
            self.occ[:, :edge] = self.occ[:, -edge:] = 1
        self.parts = []

    def best_spot(self, variants):
        """(score, variant, row, col) for the lowest, then leftmost, free spot."""
        best = None
        for v in variants:
            h, w = v.mask.shape
            if h > self.ny or w > self.nx:
                continue
            overlap = correlate(self.occ, v.mask, mode="valid", method="fft")
            free = np.argwhere(overlap < 0.5)
            if not len(free):
                continue
            # Lowest top edge first, then leftmost right edge.
            top = free[:, 0] + h
            right = free[:, 1] + w
            i = np.lexsort((right, top))[0]
            score = (top[i], right[i])
            if best is None or score < best[0]:
                best = (score, v, int(free[i, 0]), int(free[i, 1]))
        return best

    def place(self, name, v, row, col):
        h, w = v.mask.shape
        self.occ[row:row + h, col:col + w] += v.mask
        dx = col * self.s.res - v.origin[0]
        dy = row * self.s.res - v.origin[1]
        self.parts.append(Placed(name, affinity.translate(v.geom, dx, dy), v.angle))


def _angles(step):
    if step <= 0:
        return [0.0]
    n = max(1, round(360 / step))
    return [i * 360 / n for i in range(n)]


def _run(order, variants, s):
    sheets = []
    for name in order:
        for sheet in sheets:
            spot = sheet.best_spot(variants[name])
            if spot:
                sheet.place(name, *spot[1:])
                break
        else:
            sheet = _Sheet(s)
            spot = sheet.best_spot(variants[name])
            sheet.place(name, *spot[1:])
            sheets.append(sheet)
    return sheets


def _score(sheets):
    # Fewest boards, then the emptiest last board (most useful leftover).
    last = sheets[-1]
    return (len(sheets), sum(p.geom.area for p in last.parts))


def nest(outlines: dict, s: Settings = None, progress=None):
    """outlines: {name: shapely Polygon}. Returns a list of Boards."""
    s = s or Settings()
    if not outlines:
        return []
    variants = {}
    too_big = []
    probe = _Sheet(s)
    for name, geom in outlines.items():
        variants[name] = [_Variant(geom, a, s) for a in _angles(s.rotation_step)]
        if probe.best_spot(variants[name]) is None:
            x0, y0, x1, y1 = geom.bounds
            too_big.append(f"{name} ({x1 - x0:.2f}x{y1 - y0:.2f}in)")
    if too_big:
        raise NestError(f"won't fit on a {s.board_w:g}x{s.board_h:g} board "
                        f"with {s.margin:g}in margin: " + ", ".join(too_big))

    names = list(outlines)
    area = {n: outlines[n].area for n in names}
    long_side = {n: max(outlines[n].bounds[2] - outlines[n].bounds[0],
                        outlines[n].bounds[3] - outlines[n].bounds[1]) for n in names}
    orders = [sorted(names, key=lambda n: -area[n]),
              sorted(names, key=lambda n: -long_side[n])]
    rng = random.Random(s.seed)
    for _ in range(s.tries * 4):
        if len(orders) >= s.tries or len(names) < 2:
            break
        # Jitter the area ordering: swap a few neighbours.
        o = list(orders[0])
        for _ in range(max(1, len(o) // 4)):
            i = rng.randrange(len(o) - 1)
            o[i], o[i + 1] = o[i + 1], o[i]
        if o not in orders:
            orders.append(o)

    best = None
    for k, order in enumerate(orders[:max(1, s.tries)]):
        sheets = _run(order, variants, s)
        if best is None or _score(sheets) < _score(best):
            best = sheets
        if progress:
            progress(k + 1, len(orders), len(best))
    return [Board(sheet.parts) for sheet in best]
