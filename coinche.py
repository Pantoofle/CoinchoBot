from random import shuffle

from carte import Carte, Color, Value

class Coinche():
    def __init__(self, channel, players):
        self.channel = channel
        self.players = players
        self.deck = Carte.full_deck()
        self.goal = None
        self.trump = None
        self.hands = {}
        self.hands_msg = {}
        self.trick_msg = None
        self.trick_team_A = 0
        self.trick_team_B = 0
        self.cards_teamA = []
        self.cards_teamB = []
        self.last_trick_msg = None
        self.active_trick_msg = None
        self.active_trick = []
        self.active_player = 0
        self.leader = 0

    async def annonce(self, ctx, goal: int, trump):
        if self.goal is not None and self.trump is not None:
            await ctx.message.delete()
            await ctx.channel.send("Hey " + ctx.author.mention + " , les annonces sont déjà faites ! On modifie pas l'annonce ou l'atout pendant une partie !", delete_after = 10)
        else:
            try:
                self.trump = Color[trump.capitalize()]
            except KeyError:
                await ctx.message.delete()
                await ctx.channel.send("Déso, {} n'est pas une couleur valide".format(trump), delete_after = 10)
                return

            self.goal = goal
            await ctx.channel.send("__**Annonces :**__ " + str(self.goal) + " " + self.trump.name)
            await ctx.message.delete(delay = 5)

            await self.setup()

    async def update_tricks(self):
        await self.trick_msg.edit(
            content = "__**Plis :**__\n - {} | {} : {}\n - {} | {} : {}".format(self.players[0].mention,
                                                                                   self.players[2].mention,
                                                                                   self.trick_team_A,
                                                                                   self.players[1].mention,
                                                                                   self.players[3].mention,
                                                                                   self.trick_team_B))

    async def update_player_hand(self, player):
        await self.hands_msg[player].edit(content = "Ta main : \n - " + "\n - ".join([str(c) for c in self.hands[player]]))

    async def setup(self):
        await self.channel.send("Pour jouer : `!play <Valeur> <Couleur>`")
        self.trick_msg = await self.channel.send("__**Plis :**__")
        await self.update_tricks()
        self.last_trick_msg = await self.channel.send("__**Dernier pli :**__")
        self.active_trick_msg = await self.channel.send("__**Pli actuel :**__\n- En attente de " + self.players[self.leader].mention)

    async def deal(self):
        # Shuffle the deck
        shuffle(self.deck)

        # Deal the cards
        hands = [self.deck[::4],
                 self.deck[1::4],
                 self.deck[2::4],
                 self.deck[3::4]]

        # Send the hands to the players
        for (player, hand) in zip(self.players, hands):
            hand.sort(key=lambda c: 8*c.color.value + c.value.value, reverse=True)
            self.hands[player] = hand
            self.hands_msg[player] = await player.send("Ta main : \n - " + "\n - ".join([str(c) for c in hand]))

        self.active_player = 0
        self.active_trick = []

    async def play(self, ctx, value, trump):
        try:
            carte = Carte(value, trump)
        except KeyError:
            await ctx.message.delete()
            await ctx.channel.send(ctx.author.mention + "J'ai pas compris ta carte !", delete_after = 5)
            return

        player = ctx.author
        if player != self.players[self.active_player]:
            await ctx.message.delete()
            await ctx.channel.send(player.mention + " ce n'est pas ton tour !", delete_after = 5)
        elif carte not in self.hands[player]:
            await ctx.message.delete()
            await ctx.channel.send(player.mention + " tu n'as pas cette carte dans ta main...", delete_after = 5)
        else:
            self.hands[player].remove(carte)
            await self.update_player_hand(player)
            self.active_trick.append(carte)
            self.active_player = (self.active_player + 1) % 4
            text = self.active_trick_msg.content
            text = "\n".join(text.split('\n')[:-1])
            text += "\n - " + player.mention + " : " + str(carte)
            text += "\n - En attente de " + self.players[self.active_player].mention
            await self.active_trick_msg.edit(content = text)
            await ctx.message.delete()
            if self.active_player == self.leader:
                await self.gather()

    async def gather(self) :
        # Get the stack color
        color = self.active_trick[0].color

        # Sort the cards by strength
        stack = sorted(self.active_trick,
                       key = lambda c : c.strength(self.trump, color))
        print([(c.strength(self.trump, color), str(c)) for c in stack])

        # Find the winner
        winner = self.active_trick.index(stack[-1])
        await self.channel.send("Pli remporté par " + self.players[(self.leader + winner) % 4].mention, delete_after = 10)

        # Move actual trick to last trick message
        text = self.active_trick_msg.content.split("\n")
        text[0] = "__**Dernier pli :**__"
        text[-1] = "Pli remporté par " + self.players[(self.leader + winner) % 4].mention
        text = "\n".join(text)
        await self.last_trick_msg.edit(content = text)



        # Move to new leader
        self.leader = (self.leader + winner) % 4
        if self.leader % 2 == 0:
            self.trick_team_A += 1
            self.cards_teamA += self.active_trick
        else:
            self.trick_team_B += 1
            self.cards_teamB += self.active_trick

        self.active_trick = []
        self.active_player = self.leader

        # Update number of points of each team
        await self.update_tricks()

        if len(self.hands[self.players[0]]) == 0:
            await self.end_game()
        # Reset actual trick
        await self.active_trick_msg.edit(content = "__**Pli actuel :**__\n- En attente de " + self.players[self.leader].mention)

    async def end_game(self):
        pointsA = sum([c.points(self.trump) for c in self.cards_teamA])
        pointsB = sum([c.points(self.trump) for c in self.cards_teamB])

        await self.channel.send("__**Points (sans 10 de der' et Belotte) :**__\n - Équipe {} | {} : {}\n - {} | {} : {}".format(self.players[0].mention,
           self.players[2].mention,
           pointsA,
           self.players[1].mention,
           self.players[3].mention,
           pointsB))


