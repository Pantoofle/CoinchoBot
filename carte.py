from enum import Enum, IntEnum


class Color(Enum):
    Pique = 1
    Coeur = 2
    Trefle = 3
    Carreau = 4

    def __str__(self):
        return COLOR_EMOJI[self]


COLOR_DICT = {
    "Carreau": Color.Carreau,
    "Ca": Color.Carreau,
    "Carro": Color.Carreau,
    "K": Color.Carreau,
    "Trefle": Color.Trefle,
    "T": Color.Trefle,
    "Coeur": Color.Coeur,
    "C": Color.Coeur,
    "Co": Color.Coeur,
    "Pique": Color.Pique,
    "P": Color.Pique
}


class Value(IntEnum):
    As = 8
    Dix = 7
    Roi = 6
    Dame = 5
    Valet = 4
    Neuf = 3
    Huit = 2
    Sept = 1

    def __str__(self):
        return VALUE_EMOJI[self]


VALUE_DICT = {
    "As": Value.As,
    "A": Value.As,
    "Dix": Value.Dix,
    "10": Value.Dix,
    "Roi": Value.Roi,
    "K": Value.Roi,
    "R": Value.Roi,
    "Dame": Value.Dame,
    "D": Value.Dame,
    "Q": Value.Dame,
    "Valet": Value.Valet,
    "V": Value.Valet,
    "J": Value.Valet,
    "Neuf": Value.Neuf,
    "9": Value.Neuf,
    "Huit": Value.Huit,
    "8": Value.Huit,
    "Sept": Value.Sept,
    "7": Value.Sept
}


CARD_POINTS = {
    Value.As: 11,
    Value.Dix: 10,
    Value.Roi: 4,
    Value.Dame: 3,
    Value.Valet: 2,
    Value.Neuf: 0,
    Value.Huit: 0,
    Value.Sept: 0
}

VALUE_EMOJI = {
    Value.As: ":regional_indicator_a:",
    Value.Dix: ":keycap_ten:",
    Value.Roi: ":regional_indicator_r:",
    Value.Dame: ":regional_indicator_d:",
    Value.Valet: ":regional_indicator_v:",
    Value.Neuf: ":nine:",
    Value.Huit: ":eight:",
    Value.Sept: ":seven:"
}

COLOR_EMOJI = {
    Color.Carreau: ":diamonds:",
    Color.Trefle: "<:club:689536979792166936>",
    Color.Coeur: ":heart:",
    Color.Pique: "<:spade:689537818984316930>"
}


class Carte():
    def __init__(self, value, color):
        if type(value) == str:
            value = VALUE_DICT[value.capitalize()]
        if type(color) == str:
            color = COLOR_DICT[color.capitalize()]

        self.color = color
        self.value = value

    def __str__(self):
        return VALUE_EMOJI[self.value] + COLOR_EMOJI[self.color]

    def __eq__(self, other):
        return self.value == other.value and self.color == other.color

    def is_trump(self, trump):
        return self.trump.name.lower() == trump.lower()

    def full_deck():
        return [Carte(v, c) for c in Color for v in Value]

    def classical_order():
        return sorted([v for v in Value], reverse=True)

    def trump_order():
        return [Value.Valet,
                Value.Neuf,
                Value.As,
                Value.Dix,
                Value.Roi,
                Value.Dame,
                Value.Huit,
                Value.Sept]

    def points(self, trump):
        if self.color == trump:
            if self.value == Value.Valet:
                return 20
            elif self.value == Value.Neuf:
                return 14
            else:
                return CARD_POINTS[self.value]
        else:
            return CARD_POINTS[self.value]

    def strength(self, trump, color):
        if self.color == trump:
            if self.value == Value.Valet:
                return 26
            if self.value == Value.Neuf:
                return 25
            return self.value.value + 16
        elif self.color == color:
            return self.value.value + 8
        else:
            return self.value.value
