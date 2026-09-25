from leg.upper import upper
from shared import lower_leg_height, pin_diameter, upper_leg_height

from flatpack import t


def leg():
    (t.down(upper_leg_height).nose_left(90).punch(pin_diameter / 2, "knee-pin"))
    (
        t.down(upper_leg_height + lower_leg_height)
        .nose_left(90)
        .punch(pin_diameter / 2, "ankle-pin")
    )
    t.place(upper)
