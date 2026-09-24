from hips import hips
from shared import board_thickness
from torso import torso

from flatpack import setup, t

setup(thickness=board_thickness)


def bot():
    t.place(torso)
    t.place(hips)


t.place(bot)
