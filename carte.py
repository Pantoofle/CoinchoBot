from enum import Enum, IntEnum
from random import shuffle

class Color(Enum):
    Pique = 1,
    Coeur = 2,
    Carreau = 3,
    Trefle = 4

class Value(IntEnum):
    As    = 8,
    Dix   = 7,
    Roi   = 6,
    Dame  = 5,
    Valet = 4,
    Neuf  = 3,
    Huit  = 2,
    Sept  = 1

class Carte():
    def __init__(self, color, value):
        self.color = color
        self.value = value

    def __str__(self):
        return self.value.name + " de " + self.color.name

    def full_deck():
        return [Carte(c, v) for c in Color for v in Value]
