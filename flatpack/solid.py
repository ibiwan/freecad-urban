"""Turn a Model into FreeCAD solids and find where they collide. Needs FreeCAD."""
from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import numpy as np
import Part

MM = 25.4  # models are in inches; FreeCAD works in mm

# Overlaps smaller than this (mm^3) are faceting noise.
CLASH_TOLERANCE = 0.5

# Turtle marker arm lengths, inches.
MARK_POS = 1 / 2
MARK_NEG = 1 / 8


def _wire(coords, z):
    pts = []
    for x, y in coords:
        p = App.Vector(float(x) * MM, float(y) * MM, z)
        if not pts or (p - pts[-1]).Length > 1e-6:
            pts.append(p)
    if (pts[0] - pts[-1]).Length > 1e-6:
        pts.append(pts[0])
    return Part.makePolygon(pts)


def profile_face(geom, z=0.0):
    wires = [_wire(geom.exterior.coords, z)] + [_wire(r.coords, z) for r in geom.interiors]
    return Part.makeFace(wires, "Part::FaceMakerBullseye")


def placement(matrix4):
    m = np.array(matrix4, float)
    m[:3, 3] *= MM
    return App.Placement(App.Matrix(*[float(v) for v in m.ravel()]))


def chip_solid(chip):
    """Chip outline extruded from its turtle's z=0 up to z=thickness, in mm."""
    s = profile_face(chip.geom).extrude(App.Vector(0, 0, chip.thickness * MM))
    s.Placement = placement(chip.matrix)
    return s


def build(model):
    """{name: solid} for every chip."""
    return {n: chip_solid(c) for n, c in model.chips.items()}


def marker_axes(model):
    """Three compounds (x, y, z) of line segments, one segment per part entry."""
    arms = [[], [], []]
    for _, m in model.markers:
        o = m[:3, 3]
        for i in range(3):
            a = m[:3, i]
            p0, p1 = (o - a * MARK_NEG) * MM, (o + a * MARK_POS) * MM
            arms[i].append(Part.LineSegment(App.Vector(*map(float, p0)),
                                            App.Vector(*map(float, p1))).toShape())
    return [Part.Compound(a) if a else None for a in arms]


def marker_labels(model):
    """(part path, short name, position) per part entry: just past the up arm's tip."""
    out = []
    for name, m in model.markers:
        p = (m[:3, 3] + m[:3, 2] * (MARK_POS + 1 / 16)) * MM
        out.append((name, name.rsplit("/", 1)[-1], App.Vector(*map(float, p))))
    return out


def punch_rods(model):
    """(name, rod solid, used) per punch, spanning the chips it cut."""
    out = []
    for p in model.punches:
        axis = p.p1 - p.p0
        out.append((p.name, Part.makeCylinder(p.r * MM, float(np.linalg.norm(axis)) * MM,
                                              App.Vector(*map(float, p.p0 * MM)),
                                              App.Vector(*map(float, axis))), p.used))
    return out


@dataclass
class Clash:
    a: str
    b: str
    volume: float
    shape: object = None
    error: str = ""


def clashes(solids, tol=CLASH_TOLERANCE):
    names = list(solids)
    boxes = {n: solids[n].BoundBox for n in names}
    found = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not boxes[a].intersect(boxes[b]):
                continue
            try:
                common = solids[a].common(solids[b])
            except Part.OCCError as e:
                found.append(Clash(a, b, float("nan"), error=str(e)))
                continue
            if common.Volume > tol:
                found.append(Clash(a, b, common.Volume, common))
    return found
