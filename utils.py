from carte import Carte, Value


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
