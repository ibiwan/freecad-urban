"""flatpack: a turtle DSL for slot-together sheet models. Units are inches.

    from flatpack import *
"""
from .turtle import DSLError, Turtle, setup, t

__all__ = ["t", "setup", "Turtle", "DSLError"]
