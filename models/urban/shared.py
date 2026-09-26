from math import cos, pi, sin

board_thickness = 1 / 8
hinge_radius = 0.5
pin_diameter = 0.125
hip_dowel_diameter = 0.75
shoulder_dowel_diameter = 1
waist_hinge_diameter = 1.25

foot_height = 1.375  # ground to ankle pin
lower_leg_height = 2.375  # ankle pin to knee pin
upper_leg_height = 3.5  # knee pin to leg top
upper_leg_width = 1.5
hinge_box_height = 0.25


def n_gon(n, r, i, inradius=False):
    R = r / cos(pi / n) if inradius else r
    theta = 2 * pi / n * i
    return (R * cos(theta), R * sin(theta))


def n_gon_wire(t, n, r, offset=False, inradius=False):
    w = t.wire().jump(0, 0, "v-1")
    for i in range(n + 1):
        lbl = f"v{i}"
        w = w.line(*n_gon(n, r, i - (0.5 if offset else 0), inradius), lbl)
    return w.close()


def rect_forward(tt, w, d):
    return (
        tt.wire().jump(-w / 2, 0).line(-w / 2, d).line(w / 2, d).line(w / 2, 0).close()
    )


def rect_around(tt, w, d):
    return (
        tt.wire()
        .jump(-w / 2, -d / 2, "A")
        .line(-w / 2, d / 2, "B")
        .line(w / 2, d / 2, "C")
        .line(w / 2, -d / 2, "D")
        .close()
    )
