"""The turtle DSL. Units are inches.

The turtle is a frame: x right, y forward, z up (right-handed). It never
changes: every verb returns a new turtle, so `t.forward(2).place(leg)` leaves
`t` where it was. Inside a part, `t` is whatever turtle that part was placed
with.

    def leg():
        knee = t.forward(5 + 1/2).nose_up(20)
        knee.place(shin)
        knee.up(5/8).place(shin)

    def shin():
        outline = t.wire().jump(0, 0).line(1, 0).line(1, 4).arc(1/2, 4, -180).close()
        (outline - t.circle(1/2, 4, 1/8)).chip()

Wires are drawn in the turtle's XY plane with coordinates relative to that
turtle, never to the last pen position. arc(x, y, degrees) swings the pen
around center (x, y) at its current distance: positive degrees clockwise,
negative counterclockwise. A chip's thickness runs from the turtle's z=0 up
to z=thickness.
"""
from __future__ import annotations

import inspect
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from shapely import affinity
import shapely
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union
from shapely.validation import explain_validity

_PKG_DIR = Path(__file__).resolve().parent

# Largest allowed gap between a true arc and its polyline (inches, ~0.025mm).
ARC_TOLERANCE = 0.001
_EPS = 1e-9
# Outline booleans: points this close (inches) are snapped together, and
# pieces or holes smaller than this (square inches) are rounding noise.
SNAP = 1e-9
SLIVER = 1e-9


class DSLError(Exception):
    pass


def _caller():
    """'file.py:42' for the first stack frame outside this package."""
    for f in inspect.stack()[1:]:
        if Path(f.filename).resolve().parent != _PKG_DIR:
            return f"{Path(f.filename).name}:{f.lineno}"
    return "?"


def _rx(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rz(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _orthonormal(r):
    """Snap back to the nearest rotation (or reflection) so drift can't build up."""
    u, _, vt = np.linalg.svd(r)
    return u @ vt


# -- turtle ------------------------------------------------------------------

class Turtle:
    """An immutable frame. rot's columns are the turtle's right, forward, up in world space."""

    __slots__ = ("rot", "pos")

    def __init__(self, rot=None, pos=None):
        self.rot = np.eye(3) if rot is None else rot
        self.pos = np.zeros(3) if pos is None else pos

    def __repr__(self):
        f = lambda v: "(" + ", ".join(f"{x:.4g}" for x in v) + ")"
        return f"<Turtle at {f(self.pos)} forward {f(self.rot[:, 1])} up {f(self.rot[:, 2])}>"

    # -- moves (along the turtle's own axes) --
    def _slide(self, x=0.0, y=0.0, z=0.0):
        return Turtle(self.rot, self.pos + self.rot @ np.array([x, y, z], float))

    def forward(self, d):
        return self._slide(y=d)

    def back(self, d):
        return self._slide(y=-d)

    def right(self, d):
        return self._slide(x=d)

    def left(self, d):
        return self._slide(x=-d)

    def up(self, d):
        return self._slide(z=d)

    def down(self, d):
        return self._slide(z=-d)

    # -- turns (about the turtle's own axes) --
    def _turn(self, r):
        return Turtle(_orthonormal(self.rot @ r), self.pos)

    def nose_up(self, deg):
        return self._turn(_rx(deg))

    def nose_down(self, deg):
        return self._turn(_rx(-deg))

    def nose_right(self, deg):
        return self._turn(_rz(-deg))

    def nose_left(self, deg):
        return self._turn(_rz(deg))

    def roll_right(self, deg):
        """Right side goes down."""
        return self._turn(_ry(deg))

    def roll_left(self, deg):
        return self._turn(_ry(-deg))

    def aim(self, x0, y0, x1, y1):
        """A turtle at (x0, y0) in this turtle's plane, facing (x1, y1). Up is unchanged.

        Use it to sit on an edge you drew: t.aim(0, 2, 3, 4) is on the edge from
        (0, 2) to (3, 4), facing along it, wherever t goes.
        """
        dx, dy = x1 - x0, y1 - y0
        if math.hypot(dx, dy) < _EPS:
            raise DSLError("aim() needs two different points")
        bearing = math.degrees(math.atan2(dx, dy))   # clockwise from forward
        return self._slide(x=x0, y=y0).nose_right(bearing)

    def frame(self, p0, p1, p2):
        """A turtle at p0, facing p1, with up toward p2.

        Only the part of p2 off the p0 -> p1 line counts, so p2 just has to be
        somewhere on the side you want up to point. Points are (x, y, z) tuples
        relative to this turtle, world points from outline.world("A"), or
        turtles (their position). A mirrored turtle gives a mirrored frame.
        """
        a, b, c = (self._world_point(p) for p in (p0, p1, p2))
        fwd = b - a
        if np.linalg.norm(fwd) < _EPS:
            raise DSLError("frame() needs p0 and p1 to be different points")
        fwd = fwd / np.linalg.norm(fwd)
        up = (c - a) - ((c - a) @ fwd) * fwd
        if np.linalg.norm(up) < _EPS:
            raise DSLError("frame(): p2 is on the line through p0 and p1, so it can't set up")
        up = up / np.linalg.norm(up)
        right = np.cross(fwd, up) * np.sign(np.linalg.det(self.rot))
        return Turtle(np.column_stack([right, fwd, up]), a)

    def punch(self, r, name):
        """A round through-hole of radius r along this turtle's forward-back line.

        It only cuts chips that ask for it by name: outline.chip(punch="hip").
        The name is visible in the part that made the punch and everything
        placed inside it; the nearest one up the placement path wins.
        """
        if r <= 0:
            raise DSLError(f"punch radius must be positive, got {r}")
        _build().add_punch(self, float(r), name, _caller())

    def _world_point(self, p):
        if isinstance(p, Spot):
            return p.pos
        if isinstance(p, Turtle):
            return p.pos
        v = np.asarray(p, float).reshape(-1)
        if v.shape != (3,):
            raise DSLError(f"expected an (x, y, z) point, outline.world(name) or a turtle, got {p!r}")
        return self.rot @ v + self.pos

    def mirrored(self, axis):
        """A reflected copy: that axis of the frame points the other way.

        Everything placed with it comes out as a mirror image, so
        t.mirrored('x').place(leg) builds the other-handed leg.
        """
        i = "xyz".index(axis.lower())
        flip = np.eye(3)
        flip[i, i] = -1
        return Turtle(self.rot @ flip, self.pos)

    # -- building --
    def place(self, part, *args, **kwargs):
        """Run a part function with this turtle as its `t`. Extra arguments go to the part.

        Returns whatever the part returns, e.g. a turtle to attach the next part to.
        """
        if not callable(part):
            raise DSLError(f"place() needs a part function, got {part!r}")
        return _build().run_part(self, part, args, kwargs)

    def wire(self):
        return Wire(self)

    def circle(self, x, y, r):
        """A closed circular outline centered at (x, y) in this turtle's plane."""
        return Wire(self).jump(x, y + r).arc(x, y, 360).close()

    @property
    def matrix(self):
        m = np.eye(4)
        m[:3, :3] = self.rot
        m[:3, 3] = self.pos
        return m


# -- wires and outlines --------------------------------------------------------

class Spot:
    """A point in world space, e.g. from outline.world("A"). Pass it to turtle.frame()."""

    __slots__ = ("pos",)

    def __init__(self, pos):
        self.pos = np.asarray(pos, float)

    def __repr__(self):
        return "<Spot (" + ", ".join(f"{x:.4g}" for x in self.pos) + ")>"


def _lookup(names, p, what):
    if isinstance(p, str):
        try:
            return names[p]
        except KeyError:
            known = ", ".join(names) or "none"
            raise DSLError(f"no point named {p!r} on this {what} (named points: {known})") from None
    return (float(p[0]), float(p[1]))


class Wire:
    """An open pen path in a turtle's XY plane. Immutable, like the turtle.

    jump, line and arc take an optional last argument naming the point they end
    on, for use later: outline.aim("A", "B").
    """

    __slots__ = ("frame", "pts", "names")

    def __init__(self, frame, pts=(), names=None):
        self.frame = frame
        self.pts = tuple(pts)
        self.names = dict(names or {})

    def _add(self, *new, name=None):
        pts = list(self.pts)
        for p in new:
            if not pts or math.dist(pts[-1], p) > _EPS:
                pts.append((float(p[0]), float(p[1])))
        names = dict(self.names)
        if name is not None:
            if name in names:
                raise DSLError(f"point name {name!r} is already used in this wire")
            names[name] = pts[-1]
        return Wire(self.frame, pts, names)

    def point(self, p):
        """(x, y) for a point name or an (x, y) pair."""
        return _lookup(self.names, p, "wire")

    def distance(self, p0, p1):
        """Straight-line distance between two points (names or (x, y) pairs)."""
        return math.dist(self.point(p0), self.point(p1))

    def jump(self, x, y, name=None):
        """Put the pen down at (x, y). Only at the start of a wire."""
        if self.pts:
            raise DSLError("jump() only starts a wire; for a separate outline use another t.wire()")
        return self._add((x, y), name=name)

    def line(self, x, y, name=None):
        if not self.pts:
            raise DSLError("line() needs a starting point: begin the wire with jump(x, y)")
        return self._add((x, y), name=name)

    def arc(self, x, y, degrees, name=None):
        """Swing the pen around center (x, y), keeping its distance from the center.

        The batmobile arc: (x, y) is the lamp post, the grappling line from the
        pen to it sets the radius, and degrees is how far you swing.

        degrees > 0 turns clockwise (seen from the turtle's up), < 0 counter-
        clockwise; -360 to 360, and 0 draws nothing. The radius is however far
        the pen is from the center, so the arc always starts where the pen is.
        """
        if not self.pts:
            raise DSLError("arc() continues from the pen: begin the wire with jump(x, y)")
        if not -360 <= degrees <= 360:
            raise DSLError(f"arc degrees must be between -360 and 360, got {degrees}")
        px, py = self.pts[-1]
        r = math.hypot(px - x, py - y)
        if r < _EPS:
            raise DSLError("arc center is where the pen already is; it needs a radius")
        if degrees == 0:
            return self._add(name=name)
        start = math.atan2(px - x, py - y)       # bearing: clockwise from forward
        sweep = math.radians(degrees)
        step = 2 * math.acos(max(-1.0, 1 - ARC_TOLERANCE / r)) if r > ARC_TOLERANCE else math.pi / 2
        n = max(2, math.ceil(abs(sweep) / step))
        pts = [(x + r * math.sin(start + sweep * i / n), y + r * math.cos(start + sweep * i / n))
               for i in range(1, n + 1)]
        return self._add(*pts, name=name)

    def close(self):
        """Line back to where the wire started; returns a closed Outline."""
        pts = list(self.pts)
        if len(pts) > 1 and math.dist(pts[0], pts[-1]) <= _EPS:
            pts.pop()
        if len(pts) < 3:
            raise DSLError(f"a closed wire needs at least 3 points, got {len(pts)}")
        poly = Polygon(pts)
        if not poly.is_valid:
            raise DSLError(f"wire crosses itself ({explain_validity(poly)})")
        return Outline(self.frame, poly, self.names)


def _clean(g):
    """Drop sliver pieces and holes that are only rounding noise."""
    polys = [p for p in getattr(g, "geoms", [g]) if isinstance(p, Polygon) and p.area > SLIVER]
    polys = [Polygon(p.exterior, [r for r in p.interiors if Polygon(r).area > SLIVER]) for p in polys]
    if not polys:
        return Polygon()
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


class Outline:
    """A closed region in a turtle's plane. Combine with - + &, then .chip().

    Named points from its wires come along, so you can get turtles from them:
    at("A"), aim("A", "B"), on_edge("A", "B").
    """

    __slots__ = ("frame", "geom", "names")

    def __init__(self, frame, geom, names=None):
        self.frame = frame
        self.geom = geom
        self.names = dict(names or {})

    def __repr__(self):
        x0, y0, x1, y1 = self.geom.bounds
        pts = f" points {', '.join(self.names)}" if self.names else ""
        return f"<Outline {x1 - x0:.4g} x {y1 - y0:.4g}{pts}>"

    # -- named points --
    def point(self, p):
        """(x, y) in this outline's plane, for a point name or an (x, y) pair."""
        return _lookup(self.names, p, "outline")

    def distance(self, p0, p1):
        """Straight-line distance between two points (names or (x, y) pairs)."""
        return math.dist(self.point(p0), self.point(p1))

    def world(self, p):
        """Where a point on this outline sits in 3D, for use with turtle.frame()."""
        x, y = self.point(p)
        return Spot(self.frame.rot @ np.array([x, y, 0.0]) + self.frame.pos)

    def at(self, p):
        """A turtle at that point, oriented like the turtle the outline was drawn with."""
        x, y = self.point(p)
        return self.frame.right(x).forward(y)

    def aim(self, p0, p1):
        """A turtle at p0 facing p1, in the outline's plane."""
        return self.frame.aim(*self.point(p0), *self.point(p1))

    def on_edge(self, p0, p1):
        """A turtle standing on the side face the edge p0 -> p1 makes once it has thickness.

        It's at p0 on the chip's bottom corner, facing p1, with up pointing out
        of the chip and right pointing across the thickness. Works out which
        side is inside, so point order only sets which way it faces.
        """
        (x0, y0), (x1, y1) = self.point(p0), self.point(p1)
        base = self.frame.aim(x0, y0, x1, y1)
        if not LineString([(x0, y0), (x1, y1)]).within(self.geom.boundary.buffer(1e-6)):
            raise DSLError(f"{p0!r} -> {p1!r} isn't an edge of this outline")
        d = math.hypot(x1 - x0, y1 - y0)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (y1 - y0) / d * 1e-4, -(x1 - x0) / d * 1e-4   # a nudge to the walker's right
        if self.geom.contains(Point(mx + rx, my + ry)):
            return base.roll_left(90)
        if self.geom.contains(Point(mx - rx, my - ry)):
            return base.roll_right(90)
        raise DSLError(f"{p0!r} -> {p1!r} isn't an edge of this outline")

    # -- combining --
    def _transform(self, other):
        """Affine params taking other's plane coords into this outline's; must be coplanar."""
        if not isinstance(other, Outline):
            raise DSLError(f"expected an outline (a closed wire), got {type(other).__name__}")
        m = np.linalg.inv(self.frame.matrix) @ other.frame.matrix
        if abs(m[2, 0]) > 1e-6 or abs(m[2, 1]) > 1e-6 or abs(m[2, 3]) > 1e-6:
            raise DSLError("these outlines aren't in the same plane")
        return [m[0, 0], m[0, 1], m[1, 0], m[1, 1], m[0, 3], m[1, 3]]

    def _combine(self, other, op):
        a, b, d, e, xoff, yoff = tf = self._transform(other)
        # Rounding (turns at odd angles especially) leaves "lined up" edges a
        # hair apart; snap them together, then drop the slivers that survive.
        theirs = shapely.snap(affinity.affine_transform(other.geom, tf), self.geom, SNAP)
        geom = _clean(op(self.geom, theirs))
        names = {n: (a * x + b * y + xoff, d * x + e * y + yoff) for n, (x, y) in other.names.items()}
        names.update(self.names)          # on a clash, the left side's point wins
        return Outline(self.frame, geom, names)

    def __sub__(self, other):
        return self._combine(other, lambda g, o: g.difference(o))

    def __add__(self, other):
        return self._combine(other, lambda g, o: g.union(o))

    def __and__(self, other):
        return self._combine(other, lambda g, o: g.intersection(o))

    def chip(self, name=None, thickness=None, punch=None, no_punch=None):
        """Stamp this outline as a chip, thickness growing along the turtle's up.

        punch: a punch name, or a list of them, to cut holes through this chip.
        no_punch: punches that reach this chip on purpose but mustn't cut it
        (a cap over a dowel end); they're left out of the untagged-punch check.
        """
        g = self.geom
        if g.is_empty:
            raise DSLError("chip outline is empty")
        if not isinstance(g, Polygon):
            n = len(getattr(g, "geoms", []))
            raise DSLError(f"chip outline is in {n} separate pieces; a chip must be one piece")
        as_list = lambda v: [] if v is None else [v] if isinstance(v, str) else list(v)
        tags, skips = as_list(punch), as_list(no_punch)
        both = sorted(set(tags) & set(skips))
        if both:
            raise DSLError(f"{', '.join(map(repr, both))} is in both punch= and no_punch=")
        _build().add_chip(self.frame, g, name, thickness, _caller(), tags, skips)


# -- build context -------------------------------------------------------------

@dataclass
class Chip:
    name: str
    geom: Polygon       # outline in the chip's own plane, inches
    thickness: float    # inches
    matrix: np.ndarray  # 4x4 chip plane -> world, inches, always a proper rotation
    source: str
    mirrored: bool
    rgb: tuple = None


@dataclass
class PunchDef:
    name: str
    r: float
    origin: np.ndarray  # world, inches
    axis: np.ndarray    # unit, world
    path: tuple         # placement path of the part that made it
    source: str
    hits: list          # axis parameters of every chip surface it cut


@dataclass
class PunchRod:
    """What to draw for a punch: a rod over the span of chips it cut."""
    name: str
    r: float
    p0: np.ndarray
    p1: np.ndarray
    source: str
    used: bool


PUNCH_OVERHANG = 1 / 4   # rod drawn this far past the outermost chips it cut


def _rod_hits_chip(rod, frame, geom, thickness, min_depth=1e-3):
    """Does a punch's rod pass through a chip's material (outside any hole it already has)?

    Works on the rod's true cross-section inside the chip's thickness, so a rod
    that only touches a face (tangent) doesn't count.
    """
    inv = frame.rot.T
    a = inv @ (rod.p0 - frame.pos)
    b = inv @ (rod.p1 - frame.pos)
    d = b - a
    length = np.linalg.norm(d)
    if length < _EPS:
        return False
    n = d / length
    if abs(n[2]) < 1e-9:
        # Parallel to the chip: a strip as wide as the rod is inside the thickness.
        z = min(max(a[2], 0.0), thickness)           # depth in the chip nearest the axis
        gap = abs(z - a[2])
        if rod.r - gap < min_depth:
            return False
        half = math.sqrt(rod.r ** 2 - gap ** 2)
        footprint = LineString([a[:2], b[:2]]).buffer(half, cap_style="flat")
    else:
        # Crossing it: union of the rod's elliptical sections at a few depths.
        cos_t = abs(n[2])
        heading = math.degrees(math.atan2(n[1], n[0]))
        sections = []
        for z in np.linspace(min_depth, thickness - min_depth, 5):
            u = (z - a[2]) / d[2]
            if not 0.0 <= u <= 1.0:
                continue
            c = a + d * u
            e = affinity.scale(Point(0, 0).buffer(rod.r, quad_segs=16), 1 / cos_t, 1)
            sections.append(affinity.translate(affinity.rotate(e, heading, origin=(0, 0)), c[0], c[1]))
        if not sections:
            return False
        footprint = unary_union(sections)
    # A sliver of overlap is faceting noise from the polygonal holes.
    return geom.intersection(footprint).area > 1e-4


class Build:
    def __init__(self, name):
        self.name = name
        self.thickness = 1 / 8
        self.stack = [(Turtle(), ())]   # (turtle, path); a path is ((name, k), ...)
        self.counts = Counter()         # (parent path, part name) -> times placed
        self.raw = []                   # (path, name, frame, geom, thickness, source, punch tags, no_punch tags)
        self.entries = []               # (path, turtle) each time a part is entered
        self.punches = []               # PunchDef

    def current(self):
        return self.stack[-1][0]

    def run_part(self, turtle, part, args=(), kwargs=None):
        parent = self.stack[-1][1]
        name = getattr(part, "__name__", "part")
        if name == "<lambda>":
            name = "part"
        self.counts[(parent, name)] += 1
        path = parent + ((name, self.counts[(parent, name)]),)
        self.entries.append((path, turtle))
        self.stack.append((turtle, path))
        try:
            return part(*args, **(kwargs or {}))
        finally:
            self.stack.pop()

    def add_chip(self, frame, geom, name, thickness, source, tags=(), skips=()):
        self.raw.append((self.stack[-1][1], name, frame, geom,
                         self.thickness if thickness is None else float(thickness), source,
                         list(tags), list(skips)))

    def add_punch(self, turtle, r, name, source):
        path = self.stack[-1][1]
        for p in self.punches:
            if p.name == name and p.path == path:
                raise DSLError(f"punch {name!r} is already defined in this part (at {p.source})")
        self.punches.append(PunchDef(name, r, turtle.pos.copy(), turtle.rot[:, 1].copy(),
                                     path, source, []))

    def _find_punch(self, name, path):
        """The nearest punch with this name defined in the chip's part or one of its parents."""
        best = None
        for p in self.punches:
            if p.name == name and path[:len(p.path)] == p.path:
                if best is None or len(p.path) > len(best.path):
                    best = p
        return best

    def _apply_punch(self, p, frame, geom, thickness, where):
        """Cut punch p through a chip drawn in frame; returns the new outline."""
        inv = frame.rot.T                          # orthogonal, reflections included
        axis = inv @ p.axis
        if abs(abs(axis[2]) - 1) > 1e-6:
            raise DSLError(f"{where}: punch {p.name!r} ({p.source}) goes through this chip "
                           f"at a slant; punches have to be square to the chips they cut")
        o = inv @ (p.origin - frame.pos)
        u = -o[2] / axis[2]                        # where the axis meets the chip's z=0 plane
        x, y = o[0] + u * axis[0], o[1] + u * axis[1]
        hole = Wire(Turtle()).jump(x, y + p.r).arc(x, y, 360).close().geom
        if not geom.intersects(hole):
            raise DSLError(f"{where}: punch {p.name!r} ({p.source}) misses this chip")
        cut = _clean(geom.difference(hole))
        if not isinstance(cut, Polygon):
            n = len(getattr(cut, "geoms", []))
            raise DSLError(f"{where}: punch {p.name!r} cuts this chip into {n} pieces")
        # Record where along the punch this chip sits, for drawing the rod.
        base = frame.rot @ np.array([x, y, 0.0]) + frame.pos
        along = (base - p.origin) @ p.axis
        span = thickness * float(np.sign(p.axis @ frame.rot[:, 2]) or 1)
        p.hits += [along, along + span]
        return cut

    def finish(self):
        """Name every chip after the parts it was placed through."""
        def seg(parent, s):
            name, k = s
            return name if self.counts[(parent, name)] == 1 else f"{name}#{k}"

        def path_str(path):
            return "/".join(seg(path[:i], s) for i, s in enumerate(path))

        per_path = Counter(p for p, *_ in self.raw)
        seen = Counter()
        chips = {}
        placed = []   # (name, raw frame, punched outline, thickness, source, punches it asked for)
        for path, name, frame, geom, thickness, source, tags, skips in self.raw:
            def resolve(tag):
                p = self._find_punch(tag, path)
                if p is None:
                    visible = sorted({q.name for q in self.punches if path[:len(q.path)] == q.path})
                    raise DSLError(f"{source}: no punch named {tag!r} is visible here "
                                   f"(visible: {', '.join(visible) or 'none'})")
                return p
            asked = []
            for tag in tags:
                p = resolve(tag)
                geom = self._apply_punch(p, frame, geom, thickness, source)
                asked.append(p)
            asked += [resolve(tag) for tag in skips]   # exempt from the cross-check, not cut
            base = path_str(path)
            seen[path] += 1
            if name is None and per_path[path] == 1:
                full = base or "chip"
            else:
                leaf = name or f"chip#{seen[path]}"
                full = f"{base}/{leaf}" if base else leaf
            if full in chips:
                k = 2
                while f"{full}#{k}" in chips:
                    k += 1
                full = f"{full}#{k}"
            placed.append((full, frame, geom, thickness, source, asked))

            rot, mirrored = frame.rot, np.linalg.det(frame.rot) < 0
            if mirrored:
                # A reflected frame can't be a placement; flip the outline in x
                # and the frame's x axis instead. Same solid, proper rotation.
                flip = np.diag([-1.0, 1.0, 1.0])
                rot = rot @ flip
                geom = affinity.scale(geom, -1, 1, origin=(0, 0))
            m = np.eye(4)
            m[:3, :3] = rot
            m[:3, 3] = frame.pos
            chips[full] = Chip(full, geom, thickness, m, source, bool(mirrored))
        # Entry turtles keep their raw frame, reflection included, so a mirrored
        # part's marker shows its x axis pointing the other way.
        markers = [(path_str(path), turtle.matrix) for path, turtle in self.entries]
        rods = []
        warnings = []
        for p in self.punches:
            lo, hi = (min(p.hits), max(p.hits)) if p.hits else (0.0, 0.0)
            full = f"{path_str(p.path)}/{p.name}" if p.path else p.name
            rod = PunchRod(full, p.r, p.origin + p.axis * (lo - PUNCH_OVERHANG),
                           p.origin + p.axis * (hi + PUNCH_OVERHANG), p.source, bool(p.hits))
            rods.append(rod)
            if not rod.used:
                continue
            for cname, frame, geom, thickness, csource, asked in placed:
                if any(q is p for q in asked):
                    continue
                if _rod_hits_chip(rod, frame, geom, thickness):
                    warnings.append((f"punch {full} ({p.source}) passes through {cname} "
                                     f"({csource}), which isn't tagged with it",
                                     [f"chip:{cname}", f"punch:{full}"]))
        return Model(self.name, chips, markers, rods, warnings)


class Model:
    """What a model file produces: named chips, ready for the live view, clash check and nester."""

    def __init__(self, name, chips, markers=(), punches=(), warnings=()):
        self.name = name
        self.chips = chips
        self.markers = list(markers)    # (part name, 4x4 entry turtle), one per place()
        self.punches = list(punches)    # PunchRod, for drawing
        self.warnings = list(warnings)  # (message, [live-view ids to select])

    def __repr__(self):
        return f"<Model {self.name}: {len(self.chips)} chips>"

    def __getitem__(self, name):
        return self.chips[name]


_builds: list[Build] = []


def _build():
    if not _builds:
        _builds.append(Build("scratch"))
    return _builds[-1]


def begin(name):
    b = Build(name)
    _builds.append(b)
    return b


def end(b):
    if _builds and _builds[-1] is b:
        _builds.pop()


def setup(thickness=None):
    """Model-wide defaults. Call at the top of a model file: setup(thickness=1/8)."""
    if thickness is not None:
        _build().thickness = float(thickness)


class _Current:
    """`t`: whichever turtle the running part was placed with."""

    def __getattr__(self, attr):
        return getattr(_build().current(), attr)

    def __repr__(self):
        return repr(_build().current())


t = _Current()
