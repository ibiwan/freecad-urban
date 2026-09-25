"""Tiny demo: a stool. Delete it, or keep it as a scratchpad. Inches."""

from flatpack import *

setup(thickness=1 / 8)


def seat():
    (
        t.wire()
        .jump(-2, -3 / 2)
        .line(2, -3 / 2)
        .line(20, 3 / 2)
        .line(-2, 3 / 2)
        .close()
        - t.circle(0, 0, 1 / 2)
    ).chip()


def leg():
    # Turn to face out along +x, then pitch up so the turtle's forward points
    # at the sky: the leg is drawn standing up, thickness growing inward.
    stand = t.nose_right(90).nose_up(90)
    outline = (
        stand.wire()
        .jump(-5 / 4, 0)
        .line(5 / 4, 0)
        .line(5 / 4, 5 / 2)
        .arc(0, 5 / 2, -180)  # rounded top, over the forward side
        .close()
    )
    (outline - stand.circle(0, 5 / 2, 1 / 4)).chip()


def stool():
    t.up(3).place(seat)
    t.right(2).place(leg)  # legs poke through the seat: slots go there
    t.mirrored("x").right(2).place(leg)


t.place(stool)
