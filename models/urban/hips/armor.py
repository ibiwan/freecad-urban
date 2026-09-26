from hips.shared import (
    nether_width,
    pad,
)
from shared import (
    board_thickness,
    hip_dowel_diameter,
)

from flatpack import t


def _mount_wire(tt):
    return (
        tt.roll_left(90)
        .down(board_thickness)
        .forward(board_thickness)
        .wire()
        .jump(0, 0)
        .line(0.5, 0, "A")
        .line(0.375, hip_dowel_diameter / 2, "B")
        .line(0, hip_dowel_diameter + 2 * board_thickness, "C")
        .close()
    )


def _mounts(left_brace, right_brace):
    front_left_wire = _mount_wire(left_brace.on_edge("A", "B"))
    front_left_wire.chip()

    back_left_wire = _mount_wire(left_brace.on_edge("D", "C").left(board_thickness))
    back_left_wire.chip()

    front_right_wire = _mount_wire(right_brace.on_edge("A", "B"))
    front_right_wire.chip()

    back_right_wire = _mount_wire(right_brace.on_edge("D", "C").left(board_thickness))
    back_right_wire.chip()

    return (front_right_wire, back_left_wire)


def _plate_high(mount):
    (
        mount.on_edge("A", "B")
        .nose_left(90)
        .wire()
        .jump(0, -pad)
        .line(0, nether_width + pad)
        .line(mount.distance("A", "B"), nether_width)
        .line(mount.distance("A", "B"), 0)
        .close()
        .chip()
    )


def _plate_low(mount):
    (
        mount.on_edge("B", "C")
        .nose_left(90)
        .wire()
        .jump(0, 0)
        .line(0, nether_width)
        .line(mount.distance("B", "C"), nether_width)
        .line(mount.distance("B", "C"), 0)
        .close()
        .chip()
    )


def armor(left_brace, right_brace):
    (front_right_wire, back_left_wire) = t.place(_mounts, left_brace, right_brace)
    t.place(_plate_high, front_right_wire)
    t.place(_plate_high, back_left_wire)
    t.place(_plate_low, front_right_wire)
    t.place(_plate_low, back_left_wire)
