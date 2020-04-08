import discord
from discord.ext import commands
import random

from utils import delete_message, InvalidCardError
from coinche import Coinche, InvalidActionError, InvalidActorError, InvalidMomentError
from anounce import InvalidAnounceError


# Load the bot token
TOKEN = ""
with open(".token", "r") as f:
    TOKEN = f.readline()

bot = commands.Bot(command_prefix="!")

tables = {}
tables_msg = None
INDEX_CHAN = "tables-actives"
index_to_id = {}
index_to_id["next"] = 1

CONTROLED_ERRORS = [InvalidCardError,
                    InvalidActionError,
                    InvalidActorError,
                    InvalidMomentError,
                    InvalidAnounceError]


class InvalidCommandError(Exception):
    pass


async def invalidChannelMessage(channel):
    await channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


async def handleGenericError(e, channel):
    if type(e) in CONTROLED_ERRORS:
        await channel.send(e.args[0], delete_after=5)
    else:
        raise e


@bot.command()
async def start(ctx, p2: discord.Member, p3: discord.Member, p4: discord.Member):
    global tables
    players = [ctx.author, p2, p3, p4]
    await ctx.send("Starting a game with " + ", ".join([p.mention for p in players]), delete_after=10)

    guild = ctx.guild
    base = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False)
    }

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        players[0]: discord.PermissionOverwrite(read_messages=True),
        players[1]: discord.PermissionOverwrite(read_messages=True),
        players[2]: discord.PermissionOverwrite(read_messages=True),
        players[3]: discord.PermissionOverwrite(read_messages=True)
    }

    category = discord.utils.find(
        lambda cat: cat.name == "Tables de Coinche", ctx.guild.categories)
    if not category:
        category = await ctx.guild.create_category("Tables de Coinche", overwrites=base)

    channel = await ctx.guild.create_text_channel(
        name="table-coinche",
        category=category,
        overwrites=overwrites
    )

    vocal_channel = await ctx.guild.create_voice_channel(
        name="table-coinche",
        category=category,
        overwrites=overwrites
    )

    await delete_message(ctx.message)
    # Register the table in the index list
    index = index_to_id["next"]
    index_to_id[index] = channel.id
    index_to_id["next"] += 1
    # Create the table
    tables[channel.id] = Coinche(channel, vocal_channel, players, index)

    await update_tables(ctx.guild)
    await tables[channel.id].start()


@bot.command()
async def annonce(ctx, goal: int, trump: str):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    # Send the anounce
    try:
        await table.annonce(ctx, goal, trump)
    except Exception as e:
        await handleGenericError(e, ctx.channel)
        return


@bot.command(aliases=["b"])
async def bet(ctx, goal: str, trump: str):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    # Send the goal
    try:
        await table.bet(ctx, goal, trump)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command()
async def coinche(ctx):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    # Try to coinche the last bet
    try:
        await table.coinche(ctx)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command(name="pass", aliases=["nik"])
async def pass_annonce(ctx):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        await table.bet(ctx, 0, None)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command(name="p")
async def play(ctx, value, *args):
    global tables
    await delete_message(ctx.message)
    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        try:
            color = args[-1]
        except IndexError:
            raise InvalidCommandError("Utilisation : `!p <valeur> <couleur>`")
        # If we are un bet phase, consider !p as a bet
        if table.bet_phase:
            await bet(ctx, value, color)
        else:
            await table.play(ctx, value, color)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command(aliases=["akor"])
async def again(ctx):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        await table.reset()
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command()
async def end(ctx):
    global tables
    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    await table.end_table()

    # Clean the table from the index and update it
    del tables[ctx.channel.id]
    await update_tables(ctx.guild)


@bot.command()
async def spectate(ctx, index: int):
    global tables
    await delete_message(ctx.message)

    # Parse the table ID
    try:
        id = index_to_id[index]
        table = tables[id]
    except KeyError:
        await ctx.channel.send("Je reconnais pas l'id de la table", delete_after=5)
        return

    await table.add_spectator(ctx.author)


@bot.command()
async def leave(ctx):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    await table.remove_spectator(ctx.author)


@bot.command()
async def swap(ctx, target: discord.Member):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        await table.swap(ctx.author, target)
    except Exception as e:
        await handleGenericError(e, ctx.channel)

    await update_tables(ctx.guild)


async def update_tables(guild):
    global tables
    global tables_msg
    global index_to_id

    txt = "__**Tables actives : **__"
    tables_down = []
    for index in index_to_id:
        id = index_to_id[index]
        try:
            table = tables[id]
            txt += "\n - [{}] : ".format(str(index))
            txt += " | ".join([p.mention for p in table.players])
        except KeyError:
            tables_down.append(index)

    for index in tables_down:
        if index != "next":
            index_to_id.pop(index)
            print("Table {} plus active. Suppression de l'index".format(index))

    if tables_msg is None:
        chan = discord.utils.find(
            lambda c: c.name == INDEX_CHAN, guild.channels)
        tables_msg = await chan.send(txt)
    else:
        await tables_msg.edit(content=txt)


@bot.command()
async def clean(ctx):
    global tables
    global bot
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        # If table not found, it may be a DM
        await invalidChannelMessage(ctx.channel)
        return

    await table.clean(bot.user)


@bot.command(aliases=["nomore"])
async def surrender(ctx):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        await table.surrender(ctx.author)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command()
async def roll(ctx, txt):
    try:
        n, _, f = txt.partition("d")
        n, f = abs(int(n)), abs(int(f))
        if n == 1:
            await ctx.send("Résultat du dé : **" + str(random.randint(1, f)) + "**")
        else:
            dices = [random.randint(1, f) for _ in range(n)]
            s = sum(dices)
            await ctx.send("Résultat des dés : (**" + "** + **".join(
                [str(v) for v in dices]) + "**) = **" + str(s) + "**")
    except ValueError:
        await delete_message(ctx.message)
        await ctx.send("Pour lancer des dés : `!roll <nb de dés>d<nombre de faces>`, par exemple `!roll 3d10`", delete_after=5)
        return

bot.run(TOKEN)
