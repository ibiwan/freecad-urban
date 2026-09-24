board_thickness = 1 / 8
hinge_radius = 0.5
hip_dowel_diameter = 0.75


def rect_forward(tt, w, d):
    return (
        tt.wire().jump(-w / 2, 0).line(-w / 2, d).line(w / 2, d).line(w / 2, 0).close()
    )


def rect_around(tt, w, d):
    return (
        tt.wire()
        .jump(-w / 2, -d / 2)
        .line(-w / 2, d / 2)
        .line(w / 2, d / 2)
        .line(w / 2, -d / 2)
        .close()
    )
