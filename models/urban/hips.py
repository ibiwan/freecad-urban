from flatpack import t
from models.urban.leg.leg import leg


def hips():
    t.circle(0, 0, 1).chip()
    t.left(2).down(1 / 4).place(leg)
    t.right(2).down(1 / 4).place(leg)
