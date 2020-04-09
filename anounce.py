from carte import COLOR_DICT, Color

TRUMP_DICT = {
    "Ta": [Color.Pique, Color.Coeur, Color.Trefle, Color.Carreau],
    "Toutat": [Color.Pique, Color.Coeur, Color.Trefle, Color.Carreau],
    "Toutatout": [Color.Pique, Color.Coeur, Color.Trefle, Color.Carreau],
    "Sa": [],
    "Sansat": [],
    "Sansatout": []
}


class InvalidAnounceError(Exception):
    pass


class Anounce():
    def __init__(self, goal, trump):
        # Parse the goal
        self.capot = (goal == "capot")
        self.generale = (goal == "generale")
        if self.capot or self.generale:
            goal = 182
            if self.generale:
                goal += 1
        else:
            try:
                goal = int(goal)
            except ValueError:
                raise InvalidAnounceError("Valeur de l'annonce non reconnue")

        self.goal = int(goal)

        self.coinchee = False

        # Parse the trump
        trump = trump.capitalize()
        try:
            self.trumps = TRUMP_DICT[trump]
        except KeyError:
            try:
                self.trumps = [COLOR_DICT[trump]]
            except KeyError:
                raise InvalidAnounceError("Atout non reconnu")

    def __le__(self, other):
        if other is None:
            goal = 0
        else:
            goal = other.goal
        return self.goal <= goal

    def __str__(self):
        r = str(self.goal) + " "
        if self.capot:
            r = "Capot "
        elif self.generale:
            r = "Générale "

        c = ""
        if self.coinchee:
            c = " coinchée"

        t = ""
        if len(self.trumps) == 0:
            t = "Sans Atout"
        elif len(self.trumps) == 4:
            t = "Tout Atout"
        else:
            t = str(self.trumps[0])

        return r + t + c

    def coinche(self):
        self.coinchee = True

    def who_wins_game(self, results, pointsA, pointsB, taker):
        # Check generale : taker takes all the tricks
        if self.generale:
            if results[taker.index][1] == 8:
                return taker.team
            else:
                return (taker.team + 1) % 2

        # Check capot : team taker takes all the tricks
        if self.capot:
            if (results[taker.index][1] +
                    results[(taker.index + 2) % 4][1] == 8):
                return taker.team
            else:
                return (taker.team + 1) % 2

        # Else it is a normal game
        team_points = [pointsA, pointsB][taker.team]

        if team_points >= self.goal:
            return taker.team
        else:
            return (taker.team + 1) % 2
