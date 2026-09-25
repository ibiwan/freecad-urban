"""./fp <command> <model.py>   (run ./fp -h for the list)"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from . import loader

REPO = Path(__file__).resolve().parent.parent


def cmd_info(args):
    m = loader.load(args.model)
    print(f"{m.name}: {len(m.chips)} chips (inches)")
    w = max([len(n) for n in m.chips] + [4])
    total = 0.0
    for n, c in m.chips.items():
        x0, y0, x1, y1 = c.geom.bounds
        total += c.geom.area
        flag = "  mirrored" if c.mirrored else ""
        print(f"  {n:<{w}}  {x1 - x0:6.3f} x {y1 - y0:6.3f}  t={c.thickness:.3f}  "
              f"{c.geom.area:6.2f} in²  {c.source}{flag}")
    print(f"  total part area {total:.1f} in² "
          f"(a 12x12 board is 144 in², so at least {total / 144:.2f} boards)")


def cmd_nest(args):
    from . import export, nest
    m = loader.load(args.model)
    by_t = {}
    for n, c in m.chips.items():
        by_t.setdefault(c.thickness, {})[n] = c.geom
    s = nest.Settings(board_w=args.board, board_h=args.board, margin=args.margin, gap=args.gap,
                      rotation_step=args.rot, res=args.res, tries=args.tries)
    if args.kerf >= s.gap:
        sys.exit(f"--kerf ({args.kerf}) must be smaller than --gap ({s.gap})")
    out_root = Path(args.out) if args.out else REPO / "out" / m.name
    for t, outlines in sorted(by_t.items()):
        t0 = time.time()
        sub = out_root if len(by_t) == 1 else out_root / f"t{t:g}in"
        try:
            boards = nest.nest(outlines, s, progress=lambda k, n, b: print(
                f"\r  t={t:g}in: try {k}/{n}, best {b} board(s)", end="", flush=True))
        except nest.NestError as e:
            sys.exit(f"\n{e}")
        files = export.write_all(boards, s, sub, m.name, kerf=args.kerf, labels=not args.no_labels)
        print(f"\r  t={t:g}in: {len(outlines)} chips -> {len(boards)} board(s) "
              f"in {time.time() - t0:.1f}s" + " " * 10)
        for i, b in enumerate(boards, 1):
            print(f"    board {i}: {len(b.parts):2d} parts, "
                  f"{100 * b.used_area() / (s.board_w * s.board_h):3.0f}% used")
        print(f"    wrote {sub}/ (board_NN.svg, board_NN.dxf, preview.svg)")


def cmd_check(args):
    from . import solid
    m = loader.load(args.model)
    solids = solid.build(m)
    bad = [n for n, sh in solids.items() if not sh.isValid()]
    for n in bad:
        print(f"invalid solid: {n} ({m[n].source})")
    for text, _ in m.warnings:
        print(f"warning: {text}")
    found = solid.clashes(solids)
    for c in found:
        what = f"check failed: {c.error}" if c.error else f"{c.volume:.0f} mm³"
        print(f"clash: {c.a} x {c.b}  {what}  ({m[c.a].source}, {m[c.b].source})")
    print(f"{len(solids)} solids, {len(found)} clash(es), {len(m.warnings)} warning(s)")
    return 1 if (bad or found or m.warnings) else 0


def cmd_live(args):
    app = Path(os.environ.get("FREECAD_APP", "/Applications/FreeCAD.app"))
    exe = app / "Contents" / "MacOS" / "FreeCAD"
    env = dict(os.environ, FLATPACK_MODEL=str(Path(args.model).resolve()))
    subprocess.Popen([str(exe), str(REPO / "FlatpackLive.FCMacro")], env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print(f"launched FreeCAD watching {args.model}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="fp", description="flatpack model tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("info", help="list chips and sizes")
    a.set_defaults(fn=cmd_info)

    a = sub.add_parser("nest", help="pack chips onto boards, write SVG + DXF")
    a.add_argument("--board", type=float, default=12, help="square board size, in (12)")
    a.add_argument("--margin", type=float, default=0.2, help="board edge margin, in (0.2)")
    a.add_argument("--gap", type=float, default=0.125, help="space between parts, in (0.125)")
    a.add_argument("--kerf", type=float, default=0, help="laser kerf to compensate, in (0 = off)")
    a.add_argument("--rot", type=float, default=90, help="rotation step, degrees; 0 = never rotate (90)")
    a.add_argument("--res", type=float, default=1/32, help="nesting grid, in (1/32)")
    a.add_argument("--tries", type=int, default=6, help="orderings to try (6)")
    a.add_argument("--no-labels", action="store_true", help="omit part-name text")
    a.add_argument("-o", "--out", help="output dir (out/<model name>)")
    a.set_defaults(fn=cmd_nest)

    a = sub.add_parser("check", help="build solids and report clashes (needs FreeCAD)")
    a.set_defaults(fn=cmd_check)

    a = sub.add_parser("live", help="open FreeCAD with the live view on this model")
    a.set_defaults(fn=cmd_live)

    for a in sub.choices.values():
        a.add_argument("model", help="model .py file")
    args = p.parse_args(argv)
    return args.fn(args) or 0
