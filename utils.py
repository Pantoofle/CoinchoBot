from carte import Carte, Value
import discord
from random import randint


async def append_line(msg, line):
    content = msg.content
    content += "\n" + line
    await msg.edit(content=content)


async def remove_last_line(msg):
    content = msg.content.split("\n")[:-1]
    content = "\n".join(content)
    await msg.edit(content=content)


async def modify_line(msg, index, newline):
    content = msg.content.split("\n")
    content[index] = newline
    content = "\n".join(content)
    await msg.edit(content=content)


def check_belotte(hands, trumps):
    if len(trumps) != 1:
        return False
    trump = trumps[0]
    for hand in hands:
        if (Carte(Value.Dame, trump) in hand
                and Carte(Value.Roi, trump) in hand):
            return True
    return False


def who_wins_trick(stack, trumps):
    # Get the stack color
    color = stack[0][0].color

    # Sort the cards by strength
    stack = sorted(stack,
                   key=lambda entry: entry[0].strength(trumps, color))

    # Find the winner
    return stack[-1][1]


async def delete_message(m):
    try:
        await m.delete()
    except discord.errors.NotFound:
        print("Message not found. Passing.")


def shuffle_deck(deck):
    # Step 1 : cut the deck at a random point
    pos = randint(1, len(deck) - 1)
    deck = deck[pos:] + deck[:pos]
    return deck


def deal_deck(deck):
    hands = [[], [], [], []]
    # First deal 3 cards to each
    for h in hands:
        h += deck[:3]
        deck = deck[3:]
    # Do it a second time
    for h in hands:
        h += deck[:3]
        deck = deck[3:]
    # Then deal 2 cards each
    for h in hands:
        h += deck[:2]
        deck = deck[2:]

    return hands


# The different possibilities if someone tries to play a card:
OK = 0
WRONG_COLOR = 1
TRUMP = 2
LOW_TRUMP = 3


def valid_card(carte, trick, trumps, player_hand):
    """Check if the player has the right to play `carte`."""
    # No card has been played, so the player can play anything.
    if trick == []:
        return OK

    color = trick[0].color
    has_trumps = any([c.color in trumps for c in player_hand])
    has_color = any([c.color == color for c in player_hand])
    # The highest card played in the trick:
    highest_trick = max([c.strength(trumps, color) for c in trick])
    # The highest card in the player's hand:
    highest_player = max([c.strength(trumps, color) for c in player_hand])

    if color in trumps:
        if not has_color:
            return OK
        if carte.color != color:
            return WRONG_COLOR
        if carte.strength(trumps, color) < highest_trick < highest_player:
            return LOW_TRUMP
    else:
        if has_color:
            if carte.color != color:
                return WRONG_COLOR
        else:
            if len(trick) >= 2 and \
               trick[-2].strength(trumps, color) == highest_trick:
                # The partner has played the highest card in the trick, so the
                # player can play anything.
                return OK
            if not has_trumps:
                return OK
            if carte.color not in trumps:
                return TRUMP
            if carte.strength(trumps, color) < highest_trick < highest_player:
                return LOW_TRUMP
    # If all tests passed, it's ok
    return OK
