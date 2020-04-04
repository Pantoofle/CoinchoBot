from carte import COLOR_DICT, Color

TRUMP_DICT = {
    "Ta": [Color.Pique, Color.Coeur, Color.Trefle, Color.Carreau],
    "Toutat": [Color.Pique, Color.Coeur, Color.Trefle, Color.Carreau],
    "Toutatout": [Color.Pique, Color.Coeur, Color.Trefle, Color.Carreau],
    "Sa": [],
    "Sansat": [],
    "Sansatout": []
}


class Anounce():
    def __init__(self, goal, trump, capot, generale):
        self.goal = int(goal)
        self.capot = capot
        self.generale = generale
        self.coinchee = False
        trump = trump.capitalize()
        self.trumps = TRUMP_DICT.get(trump, COLOR_DICT[trump])

    def __lt__(self, other):
        if other is None:
            goal = 0
        else:
            goal = other.goal
        return self.goal < goal

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

    def count_points(self, cards_won, players):
        cards = [cards_won[p] for p in players]
        # Count the number of tricks and points of each player
        points = [sum([c.points(self.trumps) for c in stack])
                  for stack in cards]
        tricks = [len(stack)//4 for stack in cards]
        return [(p, t) for p, t in zip(points, tricks)]

    def who_wins_game(self, results, pointsA, pointsB, taker_index):
        print(results, pointsA, pointsB, taker_index)
        # Check generale : taker takes all the tricks
        if self.generale:
            print("Générale !")
            if results[taker_index][1] == 8:
                return taker_index % 2
            else:
                return (taker_index + 1) % 2

        # Check capot : team taker takes all the tricks
        if self.capot:
            print("Capot !")
            if results[taker_index][1] + results[(taker_index + 2) % 4][1] == 8:
                return taker_index % 2
            else:
                return (taker_index + 1) % 2

        # Else it is a normal game
        print("Partie normale")
        team_points = [pointsA, pointsB][taker_index % 2]

        if team_points >= self.goal:
            return taker_index % 2
        else:
            return (taker_index + 1) % 2
