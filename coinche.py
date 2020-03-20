from random import shuffle
from discord import User

from carte import Carte, Color, Value, COLOR_DICT
from utils import *

class Coinche():
    def __init__(self, channel, players):
        self.channel = channel
        self.players = players
        self.deck = Carte.full_deck()
        self.goal = None
        self.trump = None
        self.bet_phase = True
        self.pass_counter = 0
        self.annonce_msg = None
        self.dealer = 0
        self.taker = 0
        self.hands = {}
        self.hands_msg = {}
        self.global_score_msg = None
        self.global_score_A = 0
        self.global_score_B = 0
        self.trick_msg = None
        self.trick_team_A = 0
        self.trick_team_B = 0
        self.cards_teamA = []
        self.cards_teamB = []
        self.pointsA = 0
        self.pointsB = 0
        self.last_trick_msg = None
        self.active_trick_msg = None
        self.active_trick = []
        self.active_player = 0
        self.leader = 0

    async def start(self):
        await self.channel.send("Hey, ça se passe ici ! " + ", ".join([p.mention for p in self.players[self.dealer:] + self.players[:self.dealer]]))
        await self.channel.send("Pour annoncer : `!bet <points> <couleur>` ou `!pass`\nPour jouer une carte : `!p <valeur> <couleur>`")
        self.annonce_msg = await self.channel.send("__**Phase d'annonce :**__\n - " + self.players[self.dealer].mention + " : ?")
        self.active_player = self.dealer
        self.bet_phase = True
        await self.deal()

    async def bet(self, ctx, goal: int, trump):
        if ctx.author != self.players[self.active_player]:
            await ctx.message.delete()
            await ctx.channel.send("C'est pas à toi d'annoncer " + ctx.author.mention, delete_after = 5)
        else:
            if goal == 0:
                self.pass_counter += 1
                if self.pass_counter == 4 and self.goal is None:
                    await self.channel.send("Personne ne prend ? On va redistribuer alors...")
                    await self.reset()
                    return
                elif self.pass_counter == 3 and self.goal is not None:
                    self.bet_phase = False
                    await append_line(self.annonce_msg, "")
                    # TODO

    async def annonce(self, ctx, goal: int, trump):
        if self.goal is not None and self.trump is not None:
            await ctx.message.delete()
            await ctx.channel.send("Hey " + ctx.author.mention + " , les annonces sont déjà faites ! On modifie pas l'annonce ou l'atout pendant une partie !", delete_after = 10)
        else:
            try:
                self.trump = COLOR_DICT[trump.capitalize()]
            except KeyError:
                await ctx.message.delete()
                await ctx.channel.send("Déso, {} n'est pas une couleur valide".format(trump), delete_after = 10)
                return

            self.goal = goal
            self.taker = ctx.author
            await ctx.channel.send("__**Annonces :**__ " + self.taker.mention + " -> " + str(self.goal) + " " + str(self.trump))
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
    async def update_global_score(self):
        await self.global_score_msg.edit(
            content = "__**Score Global :**__\n - {} | {} : {} parties\n - {} | {} : {} parties".format(self.players[0].mention,
                                                                                   self.players[2].mention,
                                                                                   self.global_score_A,
                                                                                   self.players[1].mention,
                                                                                   self.players[3].mention,
                                                                                   self.global_score_B))

    async def update_player_hand(self, player):
        await self.hands_msg[player].edit(content = "Ta main : \n - " + "\n - ".join([str(c) for c in self.hands[player]]))

    async def setup(self):
        await self.channel.send("Pour jouer : `!p <Valeur> <Couleur>`")
        self.global_score_msg = await self.channel.send("__**Score global :**__")
        await self.update_global_score()
        self.trick_msg = await self.channel.send("__**Plis :**__")
        await self.update_tricks()
        self.last_trick_msg = await self.channel.send("__**Dernier pli :**__")
        self.active_trick_msg = await self.channel.send("__**Pli actuel :**__\n- En attente de " + self.players[self.dealer].mention)

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

        self.active_player = self.dealer
        self.active_trick = []
        self.bet_phase = True

    async def play(self, ctx, value, trump):
        if self.bet_phase = True:
            await ctx.message.delete()
            await ctx.channel.send(ctx.author.mention + " on est pas dans la phase d'annonce" delete_after = 5)
            return
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
            self.active_trick.append((carte, player))
            self.active_player = (self.active_player + 1) % 4
            text = self.active_trick_msg.content
            text = "\n".join(text.split('\n')[:-1])
            text += "\n - " + player.mention + " : " + str(carte)
            text += "\n - En attente de " + self.players[self.active_player].mention
            await self.active_trick_msg.edit(content = text)
            await ctx.message.delete()
            if len(self.active_trick) == 4:
                await self.gather()

    async def gather(self) :
        # Get the stack color
        color = self.active_trick[0].color

        # Sort the cards by strength
        stack = sorted(self.active_trick,
                       key = lambda entry : entry[0].strength(self.trump, color))
        print([(c.strength(self.trump, color), str(c)) for (c, p) in stack])

        # Find the winner
        winner = self.active_trick.index(stack[-1][1])
        await self.channel.send("Pli remporté par " + winner.mention, delete_after = 5)

        # Move actual trick to last trick message
        text = self.active_trick_msg.content.split("\n")
        text[0] = "__**Dernier pli :**__"
        text[-1] = "Pli remporté par " + winner.mention
        text = "\n".join(text)
        await self.last_trick_msg.edit(content = text)

        # Move to new leader
        self.leader = self.players.index[winner]
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
            if self.leader % 2 == 0:
                self.pointsA += 10
            else:
                self.pointsB += 10

            await self.end_game()
        # Reset actual trick
        await self.active_trick_msg.edit(content = "__**Pli actuel :**__\n- En attente de " + self.players[self.leader].mention)

    async def end_game(self):
        self.pointsA += sum([c.points(self.trump) for c in self.cards_teamA])
        self.pointsB += sum([c.points(self.trump) for c in self.cards_teamB])

        await self.channel.send("__**Points (sans Belotte) :**__\n - Équipe {} | {} : {}\n - Équipe {} | {} : {}".format(self.players[0].mention,
           self.players[2].mention,
           self.pointsA,
           self.players[1].mention,
           self.players[3].mention,
           self.pointsB))

        for p in self.hands_msg:
            await self.hands_msg[p].delete()
        self.hands_msg = {}

        # Verifier si le contrat est fait
        team_taker = self.players.index(self.taker) % 2
        if (team_taker == 0 and self.pointsA >= self.goal) or (team_taker == 1 and self.pointsB < self.goal):
            winner = 0
            self.global_score_A += 1
        else:
            winner = 1
            self.global_score_B += 1

        await self.channel.send("Victoire de l'équipe {} | {} !".format(self.players[0+winner].mention,
                                                                        self.players[2+winner].mention))
        await self.update_global_score()
        await self.channel.send("Pour relancer une partie, entrez `!again`")

    async def reset(self):
        # Next dealer
        self.dealer = (self.dealer + 1) % 4

        for p in self.hands_msg:
            await self.hands_msg[p].delete()

        async for m in self.channel.history():
            await m.delete()

        self.deck = Carte.full_deck()
        self.goal = None
        self.trump = None
        self.taker = 0
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

        await self.start()
