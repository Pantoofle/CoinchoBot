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


def check_belotte(hands, trump):
    for hand in hands:
        if (Carte(Value.Dame, trump) in hand
                and Carte(Value.Roi, trump) in hand):
            return True
    return False


def who_wins_trick(stack, trump):
    # Get the stack color
    color = stack[0][0].color

    # Sort the cards by strength
    stack = sorted(stack,
                   key=lambda entry: entry[0].strength(trump, color))

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
