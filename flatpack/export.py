"""Write nested boards as laser-ready SVG and DXF, in inches.

Cut lines are red hairlines (DXF layer CUT). Part names are blue text
(DXF layer LABEL) for engraving or scoring; turn that layer off to skip them.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from shapely.ops import polylabel

CUT = "#ff0000"
LABEL = "#0000ff"


def _rings(geom):
    yield list(geom.exterior.coords)
    for r in geom.interiors:
        yield list(r.coords)


def _label_spot(geom, name):
    """Center and text height for a label that stays inside the part."""
    p = polylabel(geom, tolerance=0.02)
    room = geom.exterior.distance(p)
    for r in geom.interiors:
        room = min(room, r.distance(p))
    # Text is roughly 0.6 * size wide per character; keep it inside the free circle.
    size = max(1 / 16, min(0.16, room * 1.2, 2 * room / (0.6 * max(1, len(name)))))
    return p.x, p.y, size


def kerf_adjust(geom, kerf):
    """Grow the outline and shrink holes by half the kerf so parts come out true to size."""
    return geom.buffer(kerf / 2, join_style="mitre") if kerf else geom


def board_svg(board, s, kerf=0.0, labels=True):
    H = s.board_h

    def path(geom):
        d = []
        for ring in _rings(geom):
            d.append("M" + " L".join(f"{x:.5f},{H - y:.5f}" for x, y in ring[:-1]) + " Z")
        return " ".join(d)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.board_w:g}in" height="{H:g}in" '
           f'viewBox="0 0 {s.board_w:g} {H:g}">',
           f'<g id="cut" fill="none" stroke="{CUT}" stroke-width="0.004">']
    for p in board.parts:
        out.append(f'<path id="{escape(p.name)}" d="{path(kerf_adjust(p.geom, kerf))}"/>')
    out.append("</g>")
    if labels:
        out.append(f'<g id="label" fill="{LABEL}" font-family="Helvetica, Arial, sans-serif" '
                   f'text-anchor="middle" dominant-baseline="central">')
        for p in board.parts:
            x, y, size = _label_spot(p.geom, p.name)
            out.append(f'<text x="{x:.4f}" y="{H - y:.4f}" font-size="{size:.4f}">{escape(p.name)}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def board_dxf(board, s, kerf=0.0, labels=True):
    """Minimal R12 DXF: one closed POLYLINE per ring, inch units."""
    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009",
         "9", "$INSUNITS", "70", "1", "0", "ENDSEC",
         "0", "SECTION", "2", "ENTITIES"]
    for p in board.parts:
        for ring in _rings(kerf_adjust(p.geom, kerf)):
            L += ["0", "POLYLINE", "8", "CUT", "62", "1", "66", "1", "70", "1",
                  "10", "0", "20", "0", "30", "0"]
            for x, y in ring[:-1]:
                L += ["0", "VERTEX", "8", "CUT", "10", f"{x:.5f}", "20", f"{y:.5f}", "30", "0"]
            L += ["0", "SEQEND", "8", "CUT"]
        if labels:
            x, y, size = _label_spot(p.geom, p.name)
            L += ["0", "TEXT", "8", "LABEL", "62", "5", "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0",
                  "40", f"{size:.4f}", "1", p.name, "72", "1", "73", "2",
                  "11", f"{x:.4f}", "21", f"{y:.4f}", "31", "0"]
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"


def preview_svg(boards, s, title=""):
    """All boards side by side, filled, for eyeballing. Not for cutting."""
    gap = 0.8
    W = len(boards) * (s.board_w + gap) - gap
    H = s.board_h
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-0.4 -1.2 {W + 0.8} {H + 1.6}" '
           f'width="{(W + 0.8) * 50:.0f}" height="{(H + 1.6) * 50:.0f}" font-family="Helvetica, Arial, sans-serif">',
           '<rect x="-0.4" y="-1.2" width="100%" height="100%" fill="#ffffff"/>',
           f'<text x="0" y="-0.5" font-size="0.36">{escape(title)}</text>']
    for i, b in enumerate(boards):
        ox = i * (s.board_w + gap)
        fill = 100 * b.used_area() / (s.board_w * s.board_h)
        out.append(f'<g transform="translate({ox},0)">')
        out.append(f'<rect width="{s.board_w}" height="{H}" fill="#f4f1ea" stroke="#999" stroke-width="0.02"/>')
        out.append(f'<text x="0" y="-0.12" font-size="0.24" fill="#555">board {i + 1}: '
                   f'{len(b.parts)} parts, {fill:.0f}% used</text>')
        for p in b.parts:
            d = " ".join("M" + " L".join(f"{x:.4f},{H - y:.4f}" for x, y in ring[:-1]) + " Z"
                         for ring in _rings(p.geom))
            out.append(f'<path d="{d}" fill="#deb887" fill-rule="evenodd" stroke="#8b5a2b" stroke-width="0.016"/>')
            x, y, size = _label_spot(p.geom, p.name)
            out.append(f'<text x="{x:.4f}" y="{H - y:.4f}" font-size="{size:.4f}" text-anchor="middle" '
                       f'dominant-baseline="central" fill="#333">{escape(p.name)}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def write_all(boards, s, out_dir, name, kerf=0.0, labels=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("board_*.*"):
        old.unlink()
    written = []
    for i, b in enumerate(boards, 1):
        for ext, fn in (("svg", board_svg), ("dxf", board_dxf)):
            f = out_dir / f"board_{i:02d}.{ext}"
            f.write_text(fn(b, s, kerf, labels))
            written.append(f)
    f = out_dir / "preview.svg"
    f.write_text(preview_svg(boards, s, f"{name}: {len(boards)} board(s) "
                                        f"{s.board_w:g}x{s.board_h:g}in"))
    written.append(f)
    return written
