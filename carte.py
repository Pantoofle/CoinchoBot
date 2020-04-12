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

    @staticmethod
    def from_str(s):
        try:
            return VALUE_DICT[s.capitalize()]
        except KeyError:
            raise InvalidCardError(
                "J'ai pas compris la valeur de ta carte")

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
    "Ç": Value.Neuf,
    "Huit": Value.Huit,
    "8": Value.Huit,
    "_": Value.Huit,
    "Sept": Value.Sept,
    "7": Value.Sept,
    "È": Value.Sept
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

SA_POINTS = {
    Value.As: 19,
    Value.Dix: 10,
    Value.Roi: 4,
    Value.Dame: 3,
    Value.Valet: 2,
    Value.Neuf: 0,
    Value.Huit: 0,
    Value.Sept: 0
}

TA_POINTS = {
    Value.Valet: 14,
    Value.Neuf: 9,
    Value.As: 6,
    Value.Dix: 5,
    Value.Roi: 3,
    Value.Dame: 1,
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


class InvalidCardError(Exception):
    pass


class Carte():
    def __init__(self, value, color):
        # Parse the value
        if type(value) == str:
            try:
                value = VALUE_DICT[value.capitalize()]
            except KeyError:
                raise InvalidCardError(
                    "J'ai pas compris la valeur de ta carte")

        # Parse the color
        if type(color) == str:
            try:
                color = COLOR_DICT[color.capitalize()]
            except KeyError:
                raise InvalidCardError(
                    "J'ai pas compris la couleur de ta carte")

        self.color = color
        self.value = value

    def __str__(self):
        return VALUE_EMOJI[self.value] + COLOR_EMOJI[self.color]

    def __eq__(self, other):
        return self.value == other.value and self.color == other.color

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

    def points(self, trumps):
        # If there's a single trump
        if len(trumps) == 1:
            if self.color == trumps[0]:
                if self.value == Value.Valet:
                    return 20
                elif self.value == Value.Neuf:
                    return 14

            return CARD_POINTS[self.value]

        # All trumps
        elif len(trumps) == 4:
            return TA_POINTS[self.value]

        # No trump
        else:
            return SA_POINTS[self.value]

    def strength(self, trumps, color):
        # Start with the base strength of the card
        force = self.value.value

        # Bonus if it is a trump
        if self.color in trumps:
            force += 20
            # More bonus so that V and 9 are the strongest trumps
            if self.value == Value.Valet:
                # Set the card strength to 10, As is at 8, normal Valet is at 4
                force += 6
            if self.value == Value.Neuf:
                # Set the card strength to 9, As is at 8, normal 9 is at 3
                force += 6

        # Bonus if you are the asked color
        if self.color == color:
            force += 10

        # Results : Trump AND Color > Trump > Color > Nothing
        return force
