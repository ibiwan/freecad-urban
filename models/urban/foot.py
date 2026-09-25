from shared import board_thickness, foot_height, hinge_radius, rect_forward

from flatpack import t


def foot():
    height = foot_height - hinge_radius / 2
    width = 1.5
    length = 2.25

    (  # sole
        t.down(height)
        .back(width / 2)
        .left(width / 2)
        .wire()
        .jump(0, 0)
        .line(0, length + board_thickness)
        .line(width, length + board_thickness)
        .line(width, 0)
        .close()
        .chip()
    )

    def vertical(tt, hinge=False):
        w = (
            tt.wire()
            .jump(0, 0)
            .line(0, width, "A")
            .line(height - board_thickness, length, "B")
            .line(height - board_thickness, 0)
            .close()
        )
        if not hinge:
            return w
        c = tt.circle(0, width / 2, hinge_radius)
        return w + c

    vertical(t.back(width / 2).left(width / 2).roll_right(90), True).chip(
        punch="ankle-pin"
    )
    v = vertical(t.back(width / 2).left(board_thickness / 2).roll_right(90))
    v.chip()
    vertical(
        t.back(width / 2).right(width / 2).roll_right(90).down(board_thickness), True
    ).chip(punch="ankle-pin")

    len = v.distance("A", "B")

    def instep():
        (
            t.wire()
            .jump(-width / 2, 0)
            .line(-width / 2, len)
            .line(width / 2, len)
            .line(width / 2, 0)
            .close()
            .chip()
        )

    v.on_edge("A", "B").right(board_thickness / 2).place(instep)

    spar_w = width - 2 * board_thickness

    def spar(tt):
        return (
            tt.wire()
            .jump(0, 0)
            .line(-spar_w, 0)
            .line(-spar_w, height - board_thickness)
            .line(spar_w, height - board_thickness)
            .line(spar_w, 0)
            .close()
        )

    rect_forward(
        t.forward(hinge_radius - board_thickness).nose_down(90),
        spar_w,
        height - board_thickness,
    ).chip()
    rect_forward(
        t.back(hinge_radius).nose_down(90), spar_w, height - board_thickness
    ).chip()
    # spar(t.back(hinge_radius).nose_down(90)).chip()
    # spar(t.forward(hinge_radius - board_thickness).nose_down(90)).chip()
