from random import shuffle
from carte import Carte, Color, InvalidCardError
from utils import append_line, remove_last_line, check_belotte, \
    who_wins_trick, valid_card
from utils import delete_message, shuffle_deck, deal_deck
from anounce import Anounce, InvalidAnounceError


class InvalidActorError(Exception):
    pass


class InvalidMomentError(Exception):
    pass


class InvalidActionError(Exception):
    pass


class Coinche():
    def __init__(self, channel, vocal_channel, players, index):
        self.index = index
        self.channel = channel
        self.vocal = vocal_channel
        self.players = players
        self.deck = Carte.full_deck()
        shuffle(self.deck)
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

        # Score message
        self.global_score_msg = await self.channel.send("__**Score global :**__")
        await self.update_global_score()

        txt = "Pour annoncer : `!bet <valeur> <atout>` ou `!pass`\nLes valeurs `generale` ou `capot` sont valides"
        await self.channel.send(txt)

        self.annonce_msg = await self.channel.send(
            "__**Phase d'annonce :**__\n - " +
            self.players[self.dealer_index].mention + " : ?")

        self.active_player_index = self.dealer_index
        self.bet_phase = True
        await self.deal()

    async def bet(self, ctx, goal: int, trump):
        # Check if author is a player
        if ctx.author not in self.players:
            raise InvalidActorError(
                "Les spectateurs ne sont pas autorisés à annoncer.")

        # Check if we are in Bet Phase
        if not self.bet_phase:
            raise InvalidMomentError(
                "Tu ne peux pas faire ça hors de la phase d'annonce " +
                ctx.author.mention)

        # Check if it is the author's turn
        if ctx.author != self.players[self.active_player_index]:
            raise InvalidActorError(
                "C'est pas à toi d'annoncer " + ctx.author.mention)

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
                # Start the play phase
                await self.setup_play()
                return

            # Move to next player
            self.active_player_index = (self.active_player_index + 1) % 4
            await append_line(self.annonce_msg, " - " + self.players[self.active_player_index].mention + " : ?")
            return

        # Then it is a normal bet. Try to cast it in an announce
        anounce = Anounce(goal, trump)

        # If the player did not bet enough
        if anounce <= self.anounce:
            raise InvalidAnounceError(
                "Il faut annoncer plus que l'annonce précédente")

        self.pass_counter = 0
        self.anounce = anounce
        self.taker_index = self.active_player_index

        # Print the anounce
        await remove_last_line(self.annonce_msg)
        await append_line(self.annonce_msg, " - " + ctx.author.mention + " : " + str(self.anounce))

        # Move to next player
        self.active_player_index = (self.active_player_index + 1) % 4
        await append_line(self.annonce_msg, " - " + self.players[self.active_player_index].mention + " : ?")

    async def coinche(self, ctx):
        # Check if author is a player
        if ctx.author not in self.players:
            raise InvalidActorError(
                "Les spectateurs ne sont pas autorisés à coincher")

        # Check if we are in Bet Phase
        if not self.bet_phase:
            raise InvalidMomentError("La phase d'annonces est terminée")

        # Check if there's something to coinche
        if self.anounce is None:
            raise InvalidMomentError(
                "Il n'y a pas d'annonce à coincher pour le moment")

        # Check if the player is in opposite team from the taker (i.e he can coinche)
        if (self.taker_index) % 2 == (self.players.index(ctx.author)) % 2:
            raise InvalidActorError(
                "Ton équipe a proposé le dernier contrat. Tu ne peux pas coincher")

        # Coinche the last anounce
        self.anounce.coinche()

        # Update message
        await remove_last_line(self.annonce_msg)
        await append_line(self.annonce_msg, " - " + ctx.author.mention + " : Coinchée")

        self.bet_phase = False

        await append_line(self.annonce_msg, "Fin des annonces")

        # Start the play phase
        await self.setup_play()

    async def annonce(self, ctx, goal: int, trump, capot=False, generale=False):
        if self.bet_phase is False:
            raise InvalidMomentError("Les annonces sont déjà faites")

        if ctx.author not in self.players:
            raise InvalidActorError("Seul un joueur peut annoncer")

        self.anounce = Anounce(goal, trump, capot, generale)
        self.taker_index = self.players.index(ctx.author)
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
            content=("__**Plis :**__\n"
                     "- {} | {} : {}\n"
                     "- {} | {} : {}").format(
                self.players[0].mention,
                self.players[2].mention,
                tricksA,
                self.players[1].mention,
                self.players[3].mention,
                tricksB))

    async def update_global_score(self):
        await self.global_score_msg.edit(
            content=("__**Score Global: **__\n"
                     "- {} | {}: {} parties\n"
                     "- {} | {}: {} parties").format(
                self.players[0].mention,
                self.players[2].mention,
                self.global_score_A,
                self.players[1].mention,
                self.players[3].mention,
                self.global_score_B))

    async def update_player_hand(self, player):
        txt = "[table {}] Ta main :".format(self.index)
        for color in Color:
            txt += "\n {} : ".format(color)
            txt += "".join([str(card.value) for card in
                            self.hands[player] if card.color == color])

        await self.hands_msg[player].edit(content=txt)

    async def setup_play(self):
        for p in self.players:
            self.cards_won[p] = []

        # Sort the hands with the new trump value
        for player in self.hands:
            self.hands[player].sort(
                key=lambda c: c.strength(self.anounce.trumps, None),
                reverse=True)
            await self.update_player_hand(player)

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
        if check_belotte(hands, self.anounce.trumps):
            if team == 0:
                self.pointsA += 20
            if team == 1:
                self.pointsB += 20

    async def deal(self):
        # Shuffle the deck
        self.deck = shuffle_deck(self.deck)

        # Deal the cards
        hands = deal_deck(self.deck)

        # Send the hands to the players
        for (player, hand) in zip(self.players, hands):
            hand.sort(key=lambda c: 8*c.color.value +
                      c.value.value, reverse=True)
            self.hands[player] = hand
            self.hands_msg[player] = await player.send("[table {}]")
            await self.update_player_hand(player)

        self.active_player_index = self.dealer_index
        self.active_trick = []
        self.pass_counter = 0
        self.bet_phase = True

    async def play(self, ctx, value, trump):
        # Check if we are in play phase
        if self.bet_phase is True:
            raise InvalidMomentError("Impossible en phase d'annonce")

        if ctx.author not in self.players:
            raise InvalidActorError("Un spectateur ne peut pas jouer de carte")

        # Find the player
        player = ctx.author
        player_index = self.players.index(player)

        # Check if it is player's turn
        if player_index != self.active_player_index:
            raise InvalidMomentError("Ce n'est pas ton tour de jouer")

        # Parse the cards
        carte = Carte(value, trump)

        # Check if player has this card in hand
        if carte not in self.hands[player]:
            raise InvalidCardError("Tu n'as pas cette carte en main")

        # Check if player is allowed to play this card
        trick_cards = [c for (c, _) in self.active_trick]
        valid_card(carte, trick_cards, self.anounce.trumps, self.hands[player])

        # Remove it from the player's hand
        self.hands[player].remove(carte)
        await self.update_player_hand(player)

        # Add it to the stack
        self.active_trick.append((carte, player))

        # Move to next player but only localy, to avoid multiple parallel modification
        local_active_player_index = (self.active_player_index + 1) % 4

        # Update the message with the curent trick
        await remove_last_line(self.active_trick_msg)
        await append_line(self.active_trick_msg, " - " + player.mention + " : " + str(carte))
        await append_line(self.active_trick_msg, " - " + self.players[local_active_player_index].mention + " : ?")

        # Move to next player in the global value now that
        # the modifications are done
        self.active_player_index = local_active_player_index

        # If we have 4 cards in the stack, trigger the gathering
        if len(self.active_trick) == 4:
            await self.gather()

    async def gather(self):
        # Find the winner
        winner = who_wins_trick(self.active_trick, self.anounce.trumps)
        winner_index = self.players.index(winner)
        await self.channel.send("Pli remporté par " + winner.mention, delete_after=5)

        # Move actual trick to last trick message
        text = self.active_trick_msg.content.split("\n")
        text[0] = "__**Dernier pli :**__"
        text[-1] = "Pli remporté par " + winner.mention
        text = "\n".join(text)
        await self.last_trick_msg.edit(content=text)

        # Put the cards in the winner's card stack
        self.cards_won[winner] += [c for (c, p) in self.active_trick]
        # Empty the trick stack
        self.active_trick = []

        # Move to new leader
        self.leader_index = winner_index

        # Check if players have no more cards
        if len(self.hands[self.players[0]]) == 0:
            # Count the 10 bonus points of the last trick
            if winner_index % 2 == 0:
                self.pointsA += 10
            else:
                self.pointsB += 10
            # Trigger end game
            # Update number of points of each team
            await self.update_tricks()
            await self.end_game()
        else:
            # Reset actual trick
            await self.active_trick_msg.edit(
                content="__**Pli actuel :**__\n- "
                + self.players[self.leader_index].mention + " : ?")

            # Update number of points of each team
            await self.update_tricks()
            self.active_player_index = self.leader_index

    async def end_game(self):
        results = self.anounce.count_points(self.cards_won, self.players)

        # Print the team points
        self.pointsA += results[0][0] + results[2][0]
        self.pointsB += results[1][0] + results[3][0]
        plisA = results[0][1] + results[2][1]
        plisB = results[1][1] + results[3][1]
        txt = "__**Points d'équipe (avec Belote pour l'attaque) :**__\n"

        txt += " - Équipe {} | {} : {} points | {} plis\n".format(
            self.players[0].mention,
            self.players[2].mention,
            self.pointsA,
            plisA)

        txt += " - Équipe {} | {} : {} points | {} plis\n".format(
            self.players[1].mention,
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
        await self.channel.send("Victoire de l'équipe {} | {} !".format(
            self.players[0+winner].mention,
            self.players[2+winner].mention))

        await self.update_global_score()

        # Delete the hand messages
        for p in self.hands_msg:
            await delete_message(self.hands_msg[p])
        self.hands_msg = {}

        await self.channel.send("Pour relancer une partie, entrez `!again`")

    async def reset(self):
        # Next dealer
        self.dealer_index = (self.dealer_index + 1) % 4

        # Delete hands if remaining
        for p in self.hands_msg:
            await delete_message(self.hands_msg[p])

        # Delete all common messages
        async for m in self.channel.history():
            await delete_message(m)

        # Gather the cards to a new deck
        self.deck = sum([self.cards_won[p] for p in self.cards_won], [])

        # Reset all the variables but not the global score
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

    async def swap(self, player, target):
        if player not in self.players:
            raise InvalidActorError(
                "C'est au joueur de swap. Pas au spectateur")

        if target in self.players:
            raise InvalidActionError(
                "On échange avec un spectateur. Pas un joueur")

        # Change the entry in self.players
        index = self.players.index(player)
        self.players[index] = target

        # Change the hands if there is one
        if player in self.hands:
            self.hands[target] = self.hands.pop(player)

            # Send the new hand
            self.hands_msg[target] = await target.send("__**Ta main**__")
            await self.update_player_hand(target)

            # Delete the old hand
            await delete_message(self.hands_msg.pop(player))

        # Send notification
        await self.channel.send("{} a laissé sa place à {} !".format(
            player.mention, target.mention), delete_after=5)

    async def surrender(self, player):
        if player not in self.players:
            raise InvalidActorError("Seul un joueur peut abandonner")

        await self.channel.send("{} abandonne.".format(player.mention))

        # The player that surrenders is now the one on defence
        self.taker_index = (self.players.index(player) + 1) % 4

        # Give the active trick to the new attacker
        self.cards_won[self.players[self.taker_index]
                       ] += [c for (c, p) in self.active_trick]

        # Give the remaining hands to the new attacker
        for p in self.players:
            self.cards_won[self.players[self.taker_index]] += self.hands[p]

        # Set the goal to zero so that the attack wins
        self.anounce.goal = 0
        self.anounce.capot = False
        self.anounce.generale = False

        # Trigger end game
        await self.end_game()

    async def end_table(self):
        await self.channel.send("Cloture de la table. Merci d'avoir joué !", delete_after=5)

        # Clean the hand messages
        for p in self.hands_msg:
            await delete_message(self.hands_msg[p])

        # Clean the channels
        await delete_message(self.vocal)
        await delete_message(self.channel)

    async def add_spectator(self, target):
        # Set permissions
        await self.channel.set_permissions(target, read_messages=True)
        await self.vocal.set_permissions(target, view_channel=True)
        # Notify users
        await self.channel.send("{} a rejoint en tant que spectateurice !".format(target.mention))

    async def remove_spectator(self, target):
        # Set permissions
        await self.channel.set_permissions(target, read_messages=False)
        await self.vocal.set_permissions(target, view_channel=False)
        # Notify
        await self.channel.send("{} n'est plus spectateurice !".format(target.mention))
