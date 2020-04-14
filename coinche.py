from random import shuffle, choice
from asyncio import Lock

from carte import Carte, InvalidCardError, Value
from utils import append_line, remove_last_line, modify_line, check_belotte, \
    who_wins_trick, valid_card, OK, WRONG_COLOR, TRUMP, LOW_TRUMP
from utils import delete_message, shuffle_deck, deal_deck
from anounce import Anounce, InvalidAnounceError
from player import Player


class InvalidActorError(Exception):
    pass


class InvalidMomentError(Exception):
    pass


class InvalidActionError(Exception):
    pass


TRICK_DEFAULT_MSG = """__**Pli actuel :**__
 - ...
 - ...
 - ...
 - ..."""


# The different phases of the game:
BET_PHASE = 0
PLAY_PHASE = 1
AFTER_GAME = 2


class Coinche():
    def __init__(self, channel, vocal_channel, players, index):
        self.lock = Lock()
        self.index = index
        self.channel = channel
        self.vocal = vocal_channel

        # Create the players
        self.players = {}
        for (id, user) in enumerate(players):
            p = Player(user, id, index)
            self.players[user] = p
            self.players[id] = p

        self.all_players = [self.players[i] for i in range(4)]

        for i, p in enumerate(self.all_players):
            p.next = self.players[(i+1) % 4]

        # Register the spectators
        self.spectators = set()

        # Generate the deck
        self.deck = Carte.full_deck()
        shuffle(self.deck)

        # Variables for announces
        self.anounce = None
        self.phase = BET_PHASE
        self.pass_counter = 0
        self.annonce_msg = None

        # Score (number of games won)
        self.global_score_msg = None
        self.global_score = [0, 0]

        # Tricks (number of tricks won)
        self.trick_msg = None
        self.tricks = [0, 0]

        # Team points during a game
        self.points = [0, 0]

        # Past trick and active trick
        self.last_trick_msg = None
        self.active_trick_msg = None
        self.active_trick = []

        # Indexes
        p0 = self.players[0]
        self.active_player = p0
        self.leader = p0
        self.dealer = p0
        self.taker = p0

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

        # Anounce message
        self.annonce_msg = await self.channel.send(
            "__**Phase d'annonce :**__\n - " +
            self.dealer.mention + " : ?")

        self.active_player = self.dealer
        await self.deal()
        self.phase = BET_PHASE

    async def bet(self, ctx, goal: int, trump):
        # Check if author is a player
        if ctx.author not in self.players:
            raise InvalidActorError(
                "Les spectateurs ne sont pas autorisés à annoncer.")

        # Check if we are in Bet Phase
        if self.phase != BET_PHASE:
            raise InvalidMomentError(
                "Tu ne peux pas faire ça hors de la phase d'annonce " +
                ctx.author.mention)

        # Check if it is the author's turn
        if ctx.author != self.active_player.user:
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
                # We declare the game finished in order to reset it
                self.phase = AFTER_GAME
                await self.reset()
                return

            # Check if all players passed with someone anouncing
            if self.pass_counter == 3 and self.anounce is not None:
                await append_line(self.annonce_msg, "Fin des annonces")
                # Start the play phase
                await self.setup_play()
                return

            # Move to next player
            self.active_player = self.active_player.next
            await append_line(self.annonce_msg, " - " + self.active_player.mention + " : ?")
            return

        # Then it is a normal bet. Try to cast it in an announce
        anounce = Anounce(goal, trump)

        # If the player did not bet enough
        if anounce <= self.anounce:
            raise InvalidAnounceError(
                "Il faut annoncer plus que l'annonce précédente")

        self.pass_counter = 0
        self.anounce = anounce
        self.taker = self.active_player

        # Print the anounce
        await remove_last_line(self.annonce_msg)
        await append_line(self.annonce_msg, " - " + ctx.author.mention + " : " + str(self.anounce))

        # Move to next player
        self.active_player = self.active_player.next
        await append_line(self.annonce_msg, " - " + self.active_player.mention + " : ?")

    async def coinche(self, ctx):
        # Check if author is a player
        if ctx.author not in self.players:
            raise InvalidActorError(
                "Les spectateurs ne sont pas autorisés à coincher")

        # Check if we are in Bet Phase
        if self.phase != BET_PHASE:
            raise InvalidMomentError("La phase d'annonces est terminée")

        # Check if there's something to coinche
        if self.anounce is None:
            raise InvalidMomentError(
                "Il n'y a pas d'annonce à coincher pour le moment")

        # Check if the player is in opposite team from the taker (i.e he can coinche)
        if self.taker.team == self.players[ctx.author].team:
            raise InvalidActorError(
                "Ton équipe a proposé le dernier contrat. Tu ne peux pas coincher")

        # Coinche the last anounce
        self.anounce.coinche()

        # Update message
        await remove_last_line(self.annonce_msg)
        await append_line(self.annonce_msg, " - " + ctx.author.mention + " : Coinchée")

        await append_line(self.annonce_msg, "Fin des annonces")

        # Start the play phase
        await self.setup_play()

    async def annonce(self, ctx, goal: int, trump, capot=False, generale=False):
        if self.phase != BET_PHASE:
            raise InvalidMomentError("Les annonces sont déjà faites")

        if ctx.author not in self.players:
            raise InvalidActorError("Seul un joueur peut annoncer")

        self.anounce = Anounce(goal, trump)
        self.taker = self.players[ctx.author]

        await self.setup_play()

    async def update_tricks(self):
        cardsA = self.players[0].cards_won + \
            self.players[2].cards_won
        cardsB = self.players[1].cards_won + \
            self.players[3].cards_won

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
                self.global_score[0],
                self.players[1].mention,
                self.players[3].mention,
                self.global_score[1]))

    async def setup_play(self):
        for p in self.all_players:
            p.cards_won = []
            # Sort the hands with the new trumps
            p.sort_hand(trumps=self.anounce.trumps)
            await p.update_hand()

        self.leader = self.dealer
        # If there is a generale, change the leader and active player
        if self.anounce.generale:
            self.leader = self.taker

        # The first active player is the leader
        self.active_player = self.leader

        # Anounce message
        await self.channel.send("__**Annonces :**__ " +
                                self.taker.mention +
                                " -> " + str(self.anounce))

        # How to play message
        await self.channel.send("Pour jouer : `!p <Valeur> <Couleur>`")

        # Number of tricks taken message
        self.trick_msg = await self.channel.send("__**Plis :**__")
        await self.update_tricks()

        # Last trick message
        self.last_trick_msg = await self.channel.send("__**Dernier pli :**__")

        # Active trick message
        self.active_trick_msg = await self.channel.send(TRICK_DEFAULT_MSG)
        await modify_line(self.active_trick_msg, 1,
                          f" - {self.active_player.mention} : ?")

        # Check for belotte
        hands = [p.hand for p in self.all_players if p.team == self.taker.team]

        if check_belotte(hands, self.anounce.trumps):
            self.points[self.taker.team] += 20

        self.phase = PLAY_PHASE

    async def deal(self):
        if len(self.deck) != 32:
            raise InvalidCardError(
                "Pourquoi mon deck a pas 32 cartes ? Ya un souci !")

        # Shuffle the deck
        self.deck = shuffle_deck(self.deck)

        # Deal the cards
        hands = deal_deck(self.deck)

        # Send the hands to the players
        for (player, hand) in zip(self.all_players, hands):
            await player.receive_hand(hand)

        self.active_player = self.dealer
        self.active_trick = []
        self.pass_counter = 0

    async def play(self, ctx, value, trump):
        # Check if we are in play phase
        if self.phase != PLAY_PHASE:
            raise InvalidMomentError(
                "Impossible de jouer hors de la phase de jeu.")

        if ctx.author not in self.players:
            raise InvalidActorError("Un spectateur ne peut pas jouer de carte")

        # Find the player
        player = self.players[ctx.author]

        # Check if it is player's turn
        if player != self.active_player:
            raise InvalidMomentError("Ce n'est pas ton tour de jouer")

        if trump is None:
            # The command is `!p` or `!p <value>`.
            # Get all the possible cards:
            trick_cards = [c for (c, _) in self.active_trick]
            possible = [c for c in player.hand
                        if valid_card(c, trick_cards, self.anounce.trumps,
                                      player.hand) == OK]

            if value is not None:
                # The command is `!p <value>`.
                # We keep only the cards with the desired value.
                value = Value.from_str(value)

                possible = [c for c in possible if c.value == value]
                if possible == []:
                    raise InvalidCardError("Tu n'as pas cette carte en main")

            # If several cards are playable, choose one of them randomly
            carte = choice(possible)
        else:
            # The command is `!p <value> <color>`.
            # Parse the cards
            carte = Carte(value, trump)

            # Check if player has this card in hand
            if carte not in player.hand:
                raise InvalidCardError("Tu n'as pas cette carte en main")

            # Check if player is allowed to play this card
            trick_cards = [c for (c, _) in self.active_trick]
            res = valid_card(carte, trick_cards, self.anounce.trumps,
                             player.hand)
            if res == WRONG_COLOR:
                raise InvalidCardError("Tu dois jouer à la couleur demandée.")
            elif res == TRUMP:
                raise InvalidCardError("Tu dois couper à l'atout.")
            elif res == LOW_TRUMP:
                raise InvalidCardError("Tu dois monter à l'atout.")

        # Remove it from the player's hand
        await player.play_card(carte)

        # Add it to the stack
        self.active_trick.append((carte, player))

        # Move to next player
        self.active_player = self.active_player.next

        # Update the message with the curent trick
        cards_played = len(self.active_trick)
        await modify_line(self.active_trick_msg, cards_played,
                          f" - {player.mention} : {carte}")

        # If we have 4 cards in the stack, trigger the gathering
        if cards_played == 4:
            await self.gather()
        else:
            # Update the message and notify the next player
            await modify_line(self.active_trick_msg, cards_played + 1,
                              f" - {self.active_player.mention} : ?")

    async def gather(self):
        # Find the winner
        winner = who_wins_trick(self.active_trick, self.anounce.trumps)

        # Move actual trick to last trick message
        text = self.active_trick_msg.content.split("\n")
        text[0] = "__**Dernier pli :**__"
        text.append("Pli remporté par " + winner.mention)
        text = "\n".join(text)
        await self.last_trick_msg.edit(content=text)

        # Put the cards in the winner's card stack
        winner.cards_won += [c for (c, _) in self.active_trick]
        # Empty the trick stack
        self.active_trick = []

        # Move to new leader
        self.leader = winner

        # Check if players have no more cards
        if len(self.players[0].hand) == 0:
            # Count the 10 bonus points of the last trick
            self.points[winner.team] += 10
            # Trigger end game
            # Update number of points of each team
            await self.update_tricks()
            await self.end_game()
        else:
            # Reset actual trick
            await self.active_trick_msg.edit(content=TRICK_DEFAULT_MSG)
            await modify_line(self.active_trick_msg, 1,
                              f" - {self.leader.mention} : ?")

            # Update number of points of each team
            await self.update_tricks()
            self.active_player = self.leader

    async def end_game(self):

        points_tricks = [p.count_points(self.anounce.trumps)
                         for p in self.all_players]

        # Print the team points
        self.points[0] += points_tricks[0][0] + points_tricks[2][0]
        self.points[1] += points_tricks[1][0] + points_tricks[3][0]

        tricks = [0, 0]
        tricks[0] = points_tricks[0][1] + points_tricks[2][1]
        tricks[1] = points_tricks[1][1] + points_tricks[3][1]
        txt = "__**Points d'équipe (avec Belote pour l'attaque) :**__\n"

        txt += " - Équipe {} | {} : {} points | {} plis\n".format(
            self.players[0].mention,
            self.players[2].mention,
            self.points[0],
            tricks[0])

        txt += " - Équipe {} | {} : {} points | {} plis\n".format(
            self.players[1].mention,
            self.players[3].mention,
            self.points[1],
            tricks[1])

        await self.channel.send(txt)

        # Find the winning team
        winner_team = self.anounce.who_wins_game(points_tricks, self.points[0],
                                                 self.points[1], self.taker)

        # Increment points
        self.global_score[winner_team] += 1

        # Send results
        await self.channel.send("Victoire de l'équipe {} | {} !".format(
            self.players[0+winner_team].mention,
            self.players[2+winner_team].mention))

        await self.update_global_score()

        # Delete the hand messages
        for p in self.all_players:
            await p.clean_hand()

        await self.channel.send("Pour relancer une partie, entrez `!again`")
        self.phase = AFTER_GAME

    async def reset(self):
        if self.phase != AFTER_GAME:
            raise InvalidActionError(
                "Cette action n'est possible qu'en fin de partie.")

        # Gather the cards to a new deck
        # 1. the cards won
        self.deck = sum([p.cards_won for p in self.all_players], [])
        # 2. the cards in hand
        for p in self.all_players:
            self.deck += p.hand
        # 3. the cards in trick
        self.deck += [c for (c, _) in self.active_trick]

        # Delete all common messages
        async for m in self.channel.history():
            await delete_message(m)

        # Delete all hands messages
        for p in self.all_players:
            await p.clean_hand()

        # Reset all the variables but not the global score
        self.anounce = None
        self.taker = None

        self.trick_msg = None
        self.tricks = [0, 0]

        self.last_trick_msg = None

        self.active_trick_msg = None
        self.active_trick = []

        # Next dealer
        self.dealer = self.dealer.next
        self.active_player = self.dealer
        self.leader = self.dealer

        self.points = [0, 0]

        await self.start()

    async def swap(self, giver, receiver):
        if giver not in self.players:
            raise InvalidActorError(
                "C'est au joueur de swap. Pas au spectateur")

        if receiver in self.players:
            raise InvalidActionError(
                "On échange avec un spectateur. Pas un joueur")

        if receiver not in self.spectators:
            # Prevent from swapping with the bot or an admin who is not an
            # active specator.
            raise InvalidActionError(f"{receiver} n'est pas spectateurice")

        # Change the entry in self.players
        player = self.players[giver]
        await player.change_owner(receiver)
        self.players.pop(giver)
        self.players[receiver] = player
        self.spectators.remove(receiver)
        self.spectators.add(giver)

        # Send notification
        await self.channel.send("{} a laissé sa place à {} !".format(
            giver.mention, receiver.mention), delete_after=5)

    async def surrender(self, player):
        if self.phase != PLAY_PHASE:
            raise InvalidMomentError(
                "Impossible d'abandonner hors de la phase de jeu.")

        if player not in self.players:
            raise InvalidActorError("Seul un joueur peut abandonner")

        await self.channel.send("{} abandonne.".format(player.mention))

        # The player that surrenders is now the one on defence
        self.taker = self.players[player].next

        # Give the active trick to the new attacker
        self.taker.cards_won += [c for (c, _) in self.active_trick]
        self.active_trick = []

        # Give the remaining hands to the new attacker
        for p in self.all_players:
            self.taker.cards_won += p.hand
            await p.clean_hand()

        # Set the goal to zero so that the attack wins
        self.anounce.goal = 0
        self.anounce.capot = False
        self.anounce.generale = False

        # Trigger end game
        await self.end_game()

    async def end_table(self):
        await self.channel.send("Cloture de la table. Merci d'avoir joué !", delete_after=5)

        # Clean the hand messages
        for p in self.all_players:
            await p.clean_hand()

        # Clean the channels
        await delete_message(self.vocal)
        await delete_message(self.channel)

    async def add_spectator(self, target):
        if target in self.players:
            raise InvalidActionError(
                f"{target.mention} Tu joues déjà à cette table.")
        if target in self.spectators:
            raise InvalidActionError(
                f"{target.mention} Tu es déjà spectateurice.")
        self.spectators.add(target)

        # Set permissions
        await self.channel.set_permissions(target, read_messages=True)
        await self.vocal.set_permissions(target, view_channel=True)
        # Notify users
        await self.channel.send("{} a rejoint en tant que spectateurice !".format(target.mention))

    async def remove_spectator(self, target):
        if target not in self.spectators:
            raise InvalidActionError(
                f"{target.mention} Tu n'es pas spectateurice. Tu ne peux "
                "pas quitter la table.")
        self.spectators.remove(target)

        # Set permissions
        await self.channel.set_permissions(target, read_messages=False)
        await self.vocal.set_permissions(target, view_channel=False)
        # Notify
        await self.channel.send("{} n'est plus spectateurice !".format(target.mention))

    async def clean(self, bot):
        # Delete all messages not from CoinchoBot
        async for m in self.channel.history():
            if m.author != bot:
                await delete_message(m)

    async def print_initial_hand(self, user):
        if user not in self.players:
            raise InvalidActorError(
                f"{user.mention} Tu es spectateurice. Tu n'as pas de main à montrer")

        if self.phase == BET_PHASE:
            raise InvalidMomentError(
                f"{user.mention} Impossible de montrer sa main pendant la phase d'annonce")

        await self.players[user].print_initial_hand(self.channel)
