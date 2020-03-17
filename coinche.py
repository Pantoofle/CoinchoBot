from random import shuffle

from carte import Carte

class Coinche():
    def __init__(self, channel, players):
        self.channel = channel
        self.players = players
        self.deck = Carte.full_deck()

    async def annonce(self, ctx, goal: int, trump):
        if goal is None and trump is None:
            await ctx.message.delete()
            await ctx.channel.send("Hey " + ctx.author.mention + " , les annonces sont déjà faites ! On modifie pas l'annonce ou l'atout pendant une partie !").delete(delay = 10)
        else:
            self.goal = goal
            self.trump = trump
            await ctx.channel.send("__**Annonces :**__ " + str(self.goal) + " " + self.trump)
            await ctx.message.delete(delay = 5)
            self.last_trick = await ctx.channel.send()

    async def deal(self):
        # Shuffle the deck
        shuffle(self.deck)

        # Deal the cards
        self.hands = [self.deck[::4],
                      self.deck[1::4],
                      self.deck[2::4],
                      self.deck[3::4]]

        # Send the hands to the players
        for (player, hand) in zip(self.players, self.hands):
            await player.send("Ta main : \n - " + "\n - ".join([str(c) for c in hand]))

