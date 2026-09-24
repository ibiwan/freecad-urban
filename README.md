# freecad-urbanmech

A turtle DSL for slot-together sheet models (1/8" ply, laser cut), with a live
FreeCAD view and a nester that packs parts onto 12×12" boards. Units are inches.

## Quick start

```sh
./fp live models/example.py    # FreeCAD opens and rebuilds whenever you save a .py
./fp info models/example.py    # parts, sizes, where each is stamped
./fp check models/example.py   # clash report, headless
./fp nest models/example.py    # -> out/example/board_NN.svg/.dxf + preview.svg
./fp test                      # DSL self-tests
```

`./fp` runs FreeCAD's bundled Python, so nothing needs installing. Set
`FREECAD_APP` if FreeCAD isn't in `/Applications`. To run the live view without
`./fp live`, open FreeCAD, set **Macro ▸ Macros… ▸ User macros location** to
this folder, and run `FlatpackLive`.

## The DSL

```python
from flatpack import *
setup(thickness=1/8)

def shin():
    outline = (t.wire().jump(-1/2, 0).line(1/2, 0).line(1/2, 4)
               .arc(0, 4, 1/2, 90, -90)             # rounded end
               .close())
    (outline - t.circle(0, 4, 1/8)).chip()

def leg():
    knee = t.forward(5 + 1/2).nose_up(20)           # a variable is a saved spot
    knee.place(shin)
    knee.up(5/8).place(shin)                        # a parallel plate, 5/8" over

t.right(1 + 1/4).place(leg)
t.mirrored('x').right(1 + 1/4).place(leg)           # the other-handed leg
```

**The turtle** is a frame: x right, y forward, z up. It never changes. Every
verb returns a new turtle, so `t.forward(2).place(leg)` leaves `t` where it
was. Inside a part, `t` is the turtle that part was placed with.

| moves | turns |
|---|---|
| `forward` / `back` | `nose_up` / `nose_down` |
| `right` / `left` | `nose_right` / `nose_left` |
| `up` / `down` | `roll_right` / `roll_left` (right side down) |

Each verb is positive in its named direction, and moves and turns are always
along or about the turtle's own axes. `mirrored('x')` returns a reflected copy,
so everything placed with it comes out as a mirror image.

`aim(x0, y0, x1, y1)` returns a turtle at (x0, y0) in this turtle's plane,
facing (x1, y1), with up unchanged.

`frame(p0, p1, p2)` returns a turtle at p0, facing p1, with up toward p2. Only
the part of p2 off the p0→p1 line counts, so p2 just has to be on the side you
want up to point. Points are `(x, y, z)` relative to this turtle, world points
from `shape.world("A")`, or turtles. Called on a mirrored turtle, the result
stays mirrored.

```python
# a panel on edge v0-v1 of octagon o1, standing up toward octagon o2
t.frame(o1.world("v0"), o1.world("v1"), o2.world("v0")).place(panel)
```

**Parts** are plain functions. `turtle.place(part)` runs one, and any extra
arguments go to the part: `edge.place(slat, width)`. Calling a part twice
stamps it twice. Names come from the call path
(`stool/leg#2`), and you never type them.

**Wires** are drawn in the turtle's XY plane. Coordinates are relative to that
turtle, not to the last pen position.

- `jump(x, y)` starts the wire. `line(x, y)` draws a straight segment.
- `jump`, `line` and `arc` take an optional last argument that names the point
  they end on: `.line(0, width, "A")`.
- `arc(x, y, r, a, b)` goes around center (x, y) from bearing a to bearing b.
  Bearings are degrees clockwise from turtle-forward (0 = forward, 90 = right).
  a < b sweeps clockwise. If the pen isn't at the arc's start, a line joins it
  there.
- `close()` draws the last segment back to the start and gives you an outline.
- `t.circle(x, y, r)` is a ready-made circular outline.

**Outlines** combine with `-`, `+` and `&`, even when they were drawn with
different turtles, as long as they lie in the same plane. `.chip()` stamps an
outline as a chip whose thickness runs from the turtle's z=0 up to z=thickness.
A chip must be one connected piece.

Named points ride along on the outline, even through `-` `+` `&`, and give you
turtles without working out any angles:

- `shape.distance("A", "B")`: straight-line distance, also on an unfinished wire.
- `shape.at("A")`: at A, oriented like the turtle the outline was drawn with.
- `shape.world("A")`: A's position in 3D, for `frame()`.
- `shape.aim("A", "B")`: at A, facing B, in the chip's plane.
- `shape.on_edge("A", "B")`: standing on the side face that edge makes once the
  chip has thickness. Up points out of the chip (it works out which side is
  inside), forward runs toward B, and right runs across the thickness.

```python
shape = (tt.wire()
    .jump(0, 0)
    .line(0, width, "A")
    .line(height, length, "B")
    .line(height, 0)
    .close())
shape.chip()
shape.on_edge("A", "B").place(lid)             # lid lies on the slanted face
shape.on_edge("A", "B").forward(1).place(lid)  # 1" further along it
```

**Punches** are round through-holes for dowels, pins and access holes.
`turtle.punch(r, "name")` defines one along that turtle's forward/back line. It
only cuts chips that ask for it by name:

```python
def hips():
    t.frame(a, b, c).punch(dowel_d / 2, "hip")   # point the turtle along the dowel
    t.place(leg)                                  # chips in leg can use "hip" too
    side.chip(punch="hip")                        # or punch=["hip", "arm"]
```

- A punch name is visible in the part that made it and in everything placed
  inside it. The nearest one up the placement path wins, so a part placed
  twice gets its own punch each time.
- Holes are cut at the end of the build, so it doesn't matter whether the
  chip or the punch comes first.
- Errors: tagging a punch that isn't visible, a punch running at a slant to
  the chip, a punch that misses the chip, or one that cuts the chip in two.
- The live view draws each punch as a see-through rod across the chips it cut.
  A punch no chip uses is drawn orange and listed in the panel.

## Live view

- Watches the model's folder and `flatpack/`. Saving any `.py` rebuilds the model, and the camera stays put.
- On an error, it keeps the last good build and shows the message plus `file:line` in the Flatpack panel.
- **Clashes** are plates that pass through each other, shown in red and listed in the panel (double-click one to select it). Until tabs and slots exist, these are exactly the spots that will need joints.
- The FreeCAD document is generated from the `.py`, so it's temporary and never asks to be saved.

## Nesting

Uses true shapes, not bounding boxes, at 0/90/180/270°, and tries several
orderings to use the fewest boards. Small parts never go inside another part's
holes. Mirrored chips are cut as their mirror-image outline.

```
--board 12  --margin 0.2  --gap 0.125  --kerf 0.006  --rot 90  --res 0.03125  --tries 12
```

Cut lines are red hairlines (DXF layer `CUT`). Part names are blue (layer `LABEL`)
for scoring or engraving; turn that layer off, or pass `--no-labels`. `--kerf`
grows outlines and shrinks holes by half the kerf. Leave it at 0 if your laser
software already compensates.

## Not yet

- Tabs and slots
- Non-round punches (slots, rectangular access holes)
