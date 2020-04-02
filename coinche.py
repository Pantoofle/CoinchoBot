from random import shuffle
from carte import Carte
from utils import append_line, remove_last_line, check_belotte, who_wins_trick
from anounce import Anounce


class Coinche():
    def __init__(self, channel, vocal_channel, players):
        self.channel = channel
        self.vocal = vocal_channel
        self.players = players
        self.deck = Carte.full_deck()
        self.anounce = None
        self.bet_phase = True
        self.pass_counter = 0
        self.annonce_msg = None
        self.dealer_index = 0
        self.taker_index = 0
        self.hands = {}
        self.hands_msg = {}
        self.global_score_msg = None
        self.global_score_A = 0
        self.global_score_B = 0
        self.trick_msg = None
        self.trick_team_A = 0
        self.trick_team_B = 0
        self.cards_won = {}
        self.pointsA = 0
        self.pointsB = 0
        self.last_trick_msg = None
        self.active_trick_msg = None
        self.active_trick = []
        self.active_player_index = 0
        self.leader_index = 0

    async def start(self):
        await self.channel.send("Début de partie ! {} | {} VS {} | {}".format(
            self.players[0].mention,
            self.players[2].mention,
            self.players[1].mention,
            self.players[3].mention))

        txt = "Pour annoncer : `!bet <valeur> <atout>` ou `!pass`\nLes valeurs `generale` ou `capot` sont valides"
        await self.channel.send(txt)

        self.annonce_msg = await self.channel.send(
            "__**Phase d'annonce :**__\n - " +
            self.players[self.dealer_index].mention + " : ?")

        self.active_player_index = self.dealer_index
        self.bet_phase = True
        await self.deal()

    async def bet(self, ctx, goal: int, trump, capot=False, generale=False):
        # Check if we are in Bet Phase
        if not self.bet_phase:
            await ctx.message.delete()
            await ctx.channel.send("La phase d'annonces est terminée " +
                                   ctx.author.mention, delete_after=5)
            return

        # Check if it is the author's turn
        if ctx.author != self.players[self.active_player_index]:
            await ctx.message.delete()
            await ctx.channel.send("C'est pas à toi d'annoncer " + ctx.author.mention, delete_after=5)
            return

        # If goal is 0, the player passed
        if goal == 0:
            await remove_last_line(self.annonce_msg)
            await append_line(self.annonce_msg, " - " + ctx.author.mention + " : Passe")
            self.pass_counter += 1
            # Check if all players passed without anyone anouncing
            if self.pass_counter == 4 and self.anounce is None:
                await self.channel.send("Personne ne prend ? On va redistribuer alors...")
                await self.reset()
                return

            # Check if all players passed with someone anouncing
            if self.pass_counter == 3 and self.anounce is not None:
                self.bet_phase = False
                await append_line(self.annonce_msg, "Fin des annonces")
                await ctx.message.delete()
                # Start the play phase
                await self.setup_play()
                return

            # Move to next player
            self.active_player_index = (self.active_player_index + 1) % 4
            await append_line(self.annonce_msg, " - " + self.players[self.active_player_index].mention + " : ?")
            await ctx.message.delete()
            return

        # Then it is a normal bet. Try to cast it in an announce
        try:
            anounce = Anounce(goal, trump, capot, generale)
        except KeyError:
            await ctx.message.delete()
            await ctx.channel.send("C'est pas une annonce valide.", delete_after=5)
            return

        # If the player did not bet enough
        if anounce < self.anounce:
            await ctx.message.delete()
            await ctx.channel.send("Il faut annoncer plus que l'annonce précédente...", delete_after=5)
            return

        self.pass_counter = 0
        self.anounce = anounce
        self.taker_index = self.active_player_index

        # Print the anounce
        await remove_last_line(self.annonce_msg)
        await append_line(self.annonce_msg, " - " + ctx.author.mention + " : " + str(self.anounce))

        # Move to next player
        self.active_player_index = (self.active_player_index + 1) % 4
        await append_line(self.annonce_msg, " - " + self.players[self.active_player_index].mention + " : ?")
        await ctx.message.delete()

    async def annonce(self, ctx, goal: int, trump, capot=False, generale=False):
        if self.bet_phase is False:
            await ctx.message.delete()
            await ctx.channel.send("Les annonces sont déjà faites !", delete_after=5)
            return

        try:
            self.anounce = Anounce(goal, trump, capot, generale)
        except KeyError:
            await ctx.message.delete()
            await ctx.channel.send("C'est pas une annonce valide", delete_after=5)
            return

        self.taker_index = self.players.index(ctx.author)
        await ctx.message.delete(delay=5)
        self.bet_phase = False

        await self.setup_play()

    async def update_tricks(self):
        cardsA = self.cards_won[self.players[0]] + \
            self.cards_won[self.players[2]]
        cardsB = self.cards_won[self.players[1]] + \
            self.cards_won[self.players[3]]
        tricksA = len(cardsA) // 4
        tricksB = len(cardsB) // 4

        await self.trick_msg.edit(
            content="__**Plis :**__\n - {} | {} : {}\n - {} | {} : {}".format(self.players[0].mention,
                                                                              self.players[2].mention,
                                                                              tricksA,
                                                                              self.players[1].mention,
                                                                              self.players[3].mention,
                                                                              tricksB))

    async def update_global_score(self):
        await self.global_score_msg.edit(
            content="__**Score Global :**__\n - {} | {} : {} parties\n - {} | {} : {} parties".format(self.players[0].mention,
                                                                                                      self.players[2].mention,
                                                                                                      self.global_score_A,
                                                                                                      self.players[1].mention,
                                                                                                      self.players[3].mention,
                                                                                                      self.global_score_B))

    async def update_player_hand(self, player):
        await self.hands_msg[player].edit(content="[table {}] Ta main : \n - ".format(self.channel.id) +
                                          "\n - ".join([str(c) for c in self.hands[player]]))

    async def setup_play(self):
        for p in self.players:
            self.cards_won[p] = []

        self.leader_index = self.dealer_index
        # If there is a generale, change the leader and active player
        if self.anounce.generale:
            self.leader_index = self.taker_index

        # The first active player is the leader
        self.active_player_index = self.leader_index

        # Anounce message
        await self.channel.send("__**Annonces :**__ " + self.players[self.taker_index].mention + " -> " + str(self.anounce))
        # How to play message
        await self.channel.send("Pour jouer : `!p <Valeur> <Couleur>`")
        # Score message
        self.global_score_msg = await self.channel.send("__**Score global :**__")
        await self.update_global_score()
        # Number of tricks taken message
        self.trick_msg = await self.channel.send("__**Plis :**__")
        await self.update_tricks()
        # Last trick message
        self.last_trick_msg = await self.channel.send("__**Dernier pli :**__")
        # Active trick message
        self.active_trick_msg = await self.channel.send("__**Pli actuel :**__\n- " + self.players[self.active_player_index].mention + " : ?")

        # Check for belotte
        team = self.taker_index % 2
        hands = [self.hands[p] for p in self.players[0 + team::2]]
        if check_belotte(hands, self.anounce.trump):
            print("Belotte détectée pour la team " + str(team))
            if team == 0:
                self.pointsA += 20
            if team == 1:
                self.pointsB += 20

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
            hand.sort(key=lambda c: 8*c.color.value +
                      c.value.value, reverse=True)
            self.hands[player] = hand
            self.hands_msg[player] = await player.send("Ta main : \n - " + "\n - ".join([str(c) for c in hand]))

        self.active_player_index = self.dealer_index
        self.active_trick = []
        self.pass_counter = 0
        self.bet_phase = True

    async def play(self, ctx, value, trump):
        # Check if we are in play phase
        if self.bet_phase is True:
            await ctx.message.delete()
            await ctx.channel.send(ctx.author.mention + " on est dans la phase d'annonce, c'est pas le moment", delete_after=5)
            return

        # Try to parse the cardr
        try:
            carte = Carte(value, trump)
        except KeyError:
            await ctx.message.delete()
            await ctx.channel.send(ctx.author.mention + "J'ai pas compris ta carte !", delete_after=5)
            return

        player_index = self.players.index(ctx.author)
        player = ctx.author

        # Check if it is player's turn
        if player_index != self.active_player_index:
            await ctx.message.delete()
            await ctx.channel.send(player.mention + " ce n'est pas ton tour !", delete_after=5)
            return

        # Check if player has this card in hand
        if carte not in self.hands[player]:
            await ctx.message.delete()
            await ctx.channel.send(player.mention + " tu n'as pas cette carte dans ta main...", delete_after=5)
            return

        # Then, the card is valid, play it
        # Remove it from the player's hand
        self.hands[player].remove(carte)
        await self.update_player_hand(player)
        # Add it to the stack
        self.active_trick.append((carte, player))
        # Move to next player
        self.active_player_index = (self.active_player_index + 1) % 4

        # Update the message with the curent trick
        await remove_last_line(self.active_trick_msg)
        await append_line(self.active_trick_msg, " - " + player.mention + " : " + str(carte))
        await append_line(self.active_trick_msg, " - " + self.players[self.active_player_index].mention + " : ?")

        # Delete the author's message
        await ctx.message.delete()

        # If we have 4 cards in the stack, trigger the gathering
        if len(self.active_trick) == 4:
            await self.gather()

    async def gather(self):
        # Find the winner
        winner = who_wins_trick(self.active_trick, self.anounce.trump)
        winner_index = self.players.index(winner)
        await self.channel.send("Pli remporté par " + winner.mention, delete_after=5)

        # Move actual trick to last trick message
        text = self.active_trick_msg.content.split("\n")
        text[0] = "__**Dernier pli :**__"
        text[-1] = "Pli remporté par " + winner.mention
        text = "\n".join(text)
        await self.last_trick_msg.edit(content=text)

        # Move to new leader
        self.leader_index = winner_index
        self.active_player_index = self.leader_index

        # Put the cards in the winner's card stack
        self.cards_won[winner] += [c for (c, p) in self.active_trick]
        # Empty the trick stack
        self.active_trick = []

        # Update number of points of each team
        await self.update_tricks()

        # Check if players have no more cards
        if len(self.hands[self.players[0]]) == 0:
            # Count the 10 bonus points of the last trick
            if winner_index % 2 == 0:
                self.pointsA += 10
            else:
                self.pointsB += 10
            # Trigger end game
            await self.end_game()
        else:
            # Reset actual trick
            await self.active_trick_msg.edit(content="__**Pli actuel :**__\n- " + self.players[self.leader_index].mention + " : ?")

    async def end_game(self):
        results = self.anounce.count_points(self.cards_won, self.players)

        # Print the individual points
        # txt = "__**Points personnels :**__\n"
        # for (player, (points, tricks)) in enumerate(results):
        #     txt += " - {} : {} points | {} plis\n".format(
        #         self.players[player].mention, points, tricks)

        # Print the team points
        self.pointsA += results[0][0] + results[2][0]
        self.pointsB += results[1][0] + results[3][0]
        plisA = results[0][1] + results[2][1]
        plisB = results[1][1] + results[3][1]
        txt = "__**Points d'équipe (avec Belote) :**__\n"
        txt += " - Équipe {} | {} : {} points | {} plis\n".format(self.players[0].mention,
                                                                  self.players[2].mention,
                                                                  self.pointsA,
                                                                  plisA)
        txt += " - Équipe {} | {} : {} points | {} plis\n".format(self.players[1].mention,
                                                                  self.players[3].mention,
                                                                  self.pointsB,
                                                                  plisB)
        await self.channel.send(txt)

        # Find the winning team
        winner = self.anounce.who_wins_game(results, self.pointsA,
                                            self.pointsB, self.taker_index)

        # Increment points
        if winner == 0:
            self.global_score_A += 1
        else:
            self.global_score_B += 1

        # Send results
        await self.channel.send("Victoire de l'équipe {} | {} !".format(self.players[0+winner].mention,
                                                                        self.players[2+winner].mention))
        await self.update_global_score()

        # Delete the hand messages
        for p in self.hands_msg:
            await self.hands_msg[p].delete()
        self.hands_msg = {}

        await self.channel.send("Pour relancer une partie, entrez `!again`")

    async def reset(self):
        # Next dealer
        self.dealer_index = (self.dealer_index + 1) % 4

        # Delete hands if remaining
        for p in self.hands_msg:
            await self.hands_msg[p].delete()

        # Delete all common messages
        async for m in self.channel.history():
            await m.delete()

        # Reset all the variables but not the global score
        self.deck = Carte.full_deck()
        self.anounce = None
        self.taker_index = 0
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
        self.active_player_index = 0
        self.leader_index = 0

        self.pointsA = 0
        self.pointsB = 0

        self.bet_phase = True

        await self.start()
