from leg.leg import leg
from shared import (
    board_thickness,
    hinge_box_height,
    hip_dowel_diameter,
    n_gon,
    pin_diameter,
    rect_around,
    upper_leg_width,
    waist_hinge_diameter,
)

from flatpack import t

hip_leg_tops_delta = 0.25
plate_width = 2.25
nether_width = 1.75
dowel_brace_size = hip_dowel_diameter + 2 * board_thickness
pad = (plate_width - nether_width) / 2


def _dowel_braces():
    outer_left = rect_around(
        t.down(plate_width / 2 + board_thickness),
        dowel_brace_size,
        dowel_brace_size,
    )
    outer_left.chip(punch="hip-dowel", no_punch="hip-pin")

    outer_right = rect_around(
        t.up(plate_width / 2),
        dowel_brace_size,
        dowel_brace_size,
    )
    outer_right.chip(punch="hip-dowel", no_punch="hip-pin")

    inner_left = rect_around(
        t.down(nether_width / 2),
        dowel_brace_size,
        dowel_brace_size,
    )
    inner_left.chip(punch="hip-dowel", no_punch="hip-pin")

    inner_right = rect_around(
        t.up(nether_width / 2 - board_thickness),
        dowel_brace_size,
        dowel_brace_size,
    )
    inner_right.chip(punch="hip-dowel", no_punch="hip-pin")

    return (inner_left, inner_right)


def _lower_armor_mount_wire(tt):
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


def _lower_armor_mounts(left_brace, right_brace):
    front_left_wire = _lower_armor_mount_wire(left_brace.on_edge("A", "B"))
    front_left_wire.chip()

    back_left_wire = _lower_armor_mount_wire(
        left_brace.on_edge("D", "C").left(board_thickness)
    )
    back_left_wire.chip()

    front_right_wire = _lower_armor_mount_wire(right_brace.on_edge("A", "B"))
    front_right_wire.chip()

    back_right_wire = _lower_armor_mount_wire(
        right_brace.on_edge("D", "C").left(board_thickness)
    )
    back_right_wire.chip()

    return (front_right_wire, back_left_wire)


def _lower_armor_high(mount):
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


def _lower_armor_low(mount):
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


def _lower_armor(left_brace, right_brace):
    (front_right_wire, back_left_wire) = t.place(
        _lower_armor_mounts, left_brace, right_brace
    )
    t.place(_lower_armor_high, front_right_wire)
    t.place(_lower_armor_high, back_left_wire)
    t.place(_lower_armor_low, front_right_wire)
    t.place(_lower_armor_low, back_left_wire)


def _hex_wire(tt, r):
    w = tt.wire().jump(0, 0, "v-1")
    for i in range(0, 7):
        lbl = f"v{i}"
        w = w.line(*n_gon(6, r, i + 0.5), lbl)
    return w.close()


def _hip_lock():
    t1 = t.forward(plate_width / 2 + upper_leg_width + board_thickness).nose_down(90)
    t1.circle(0, 0, 1).chip(punch="hip-dowel", no_punch="hip-pin")
    (_hex_wire(t1.up(board_thickness), 1)).chip(punch="hip-pin", no_punch="hip-dowel")
    (_hex_wire(t1.up(board_thickness * 2), 0.75)).chip(
        punch="hip-pin", no_punch="hip-dowel"
    )
    (
        t1.up(board_thickness * 3)
        .circle(0, 0, 0.5)
        .chip(punch="hip-pin", no_punch="hip-dowel")
    )


def _hip_locks():
    t1 = t.down(
        hinge_box_height + hip_dowel_diameter / 2 + board_thickness * 2
    ).nose_right(90)
    t1.place(_hip_lock)
    t1.mirrored("y").place(_hip_lock)


def hips():
    tc = t.down(
        hip_leg_tops_delta + hip_dowel_diameter / 2 + 2 * board_thickness
    ).nose_left(90)
    tc.punch(hip_dowel_diameter / 2, "hip-dowel")
    tc.punch(pin_diameter / 2, "hip-pin")

    w = rect_around(t.down(board_thickness), plate_width, plate_width)
    c = t.down(board_thickness).circle(0, 0, waist_hinge_diameter / 2)
    (w - c).chip()

    # for i in range(4):
    #     t_outer = t.nose_right(90 * i)
    #     rect_forward(
    #         t_outer.down(board_thickness)
    #         .forward(plate_width / 2 - board_thickness)
    #         .nose_down(90),
    #         plate_width,
    #         hinge_box_height,
    #     ).chip()

    #     t_inner = t.nose_right(45 + 90 * i)
    #     rect_forward(
    #         t_inner.down(board_thickness)
    #         .forward(waist_hinge_diameter / 2)
    #         .nose_down(90),
    #         plate_width / 2,
    #         hinge_box_height,
    #     ).chip()

    rect_around(
        t.down(2 * board_thickness + hinge_box_height),
        plate_width + 2 * board_thickness,
        plate_width,
    ).chip()

    # inner_hip_braces = (
    #     t.down(hinge_box_height + hip_dowel_diameter / 2 + 2 * board_thickness)
    #     .nose_right(90)
    #     .nose_down(90)
    #     .place(_dowel_braces)
    # )

    # rect_forward(
    #     t.down(hinge_box_height + 2 * board_thickness)
    #     .forward(hip_dowel_diameter / 2)
    #     .nose_down(90),
    #     nether_width,
    #     hip_dowel_diameter,
    # ).chip()

    # rect_forward(
    #     t.down(hinge_box_height + 2 * board_thickness)
    #     .back(hip_dowel_diameter / 2 + board_thickness)
    #     .nose_down(90),
    #     nether_width,
    #     hip_dowel_diameter,
    # ).chip()

    # rect_around(
    #     t.down(3 * board_thickness + hinge_box_height + hip_dowel_diameter),
    #     plate_width,
    #     dowel_brace_size,
    # ).chip()

    # rect_around(
    #     t.down(4 * board_thickness + hinge_box_height + hip_dowel_diameter),
    #     nether_width,
    #     dowel_brace_size,
    # ).chip()

    # left_brace, right_brace = inner_hip_braces
    # t.place(_lower_armor, left_brace, right_brace)

    # t.place(_hip_locks)

    # t.left(2).down(hip_leg_tops_delta).place(leg)
    # t.right(2).down(hip_leg_tops_delta).place(leg)
