import discord
from discord.ext import commands
import random
import os
import asyncio
from dateutil import parser

from utils import delete_message
from coinche import BET_PHASE, Coinche, \
    InvalidActionError, InvalidActorError, InvalidMomentError
from anounce import InvalidAnounceError
from carte import InvalidCardError


# Load the bot token
path = os.path.dirname(os.path.abspath(__file__))
TOKEN = ""
with open(path+"/.token", "r") as f:
    TOKEN = f.readline()

bot = commands.Bot(command_prefix="!")

tables = {}
tables_msg = None
INDEX_CHAN = "tables-actives"
index_to_id = {}
index_to_id["next"] = 1
avail_timers = {}


class InvalidCommandError(Exception):
    pass


CONTROLED_ERRORS = [InvalidCardError,
                    InvalidActionError,
                    InvalidActorError,
                    InvalidMomentError,
                    InvalidAnounceError,
                    InvalidCommandError]


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
    await delete_message(ctx.message)
    players = [ctx.author, p2, p3, p4]

    # Prepare the permission modifications
    guild = ctx.guild
    base = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False)
    }

    overwrites_all = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        players[0]: discord.PermissionOverwrite(read_messages=True),
        players[1]: discord.PermissionOverwrite(read_messages=True),
        players[2]: discord.PermissionOverwrite(read_messages=True),
        players[3]: discord.PermissionOverwrite(read_messages=True)
    }

    # Create the category where we put the table
    index = index_to_id["next"]
    category = await ctx.guild.create_category(f"Table {index}", overwrites=base)

    # Create the table
    channel = await ctx.guild.create_text_channel(
        name="Zone de Jeu",
        category=category,
        overwrites=overwrites_all
    )

    # Create the vocal channel
    vocal_channel = await ctx.guild.create_voice_channel(
        name="Vocal",
        category=category,
        overwrites=overwrites_all
    )

    # Create the hands channels
    hand_channels = {}
    for p in players:
        overwrites_perso = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            p: discord.PermissionOverwrite(read_messages=True)
        }

        hand_channels[p] = await ctx.guild.create_text_channel(
            name=f"Main de {p.name}",
            category=category,
            overwrites=overwrites_perso
        )

    # Register the table in the index list
    index = index_to_id["next"]
    index_to_id[index] = channel.id
    index_to_id["next"] += 1
    # Create the table
    tables[channel.id] = Coinche(
        channel, vocal_channel, hand_channels, players, index)

    # Set all players to not dispo anymore
    for p in players:
        await is_not_dispo(p, ctx.guild)

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
        async with table.lock:
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
        async with table.lock:
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
        async with table.lock:
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
        async with table.lock:
            await table.bet(ctx, 0, None)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command(name="p")
async def play(ctx, *args):
    global tables
    await delete_message(ctx.message)
    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        # If we are in bet phase, consider !p as a bet
        if table.phase == BET_PHASE:
            try:
                value, color = args
            except ValueError:
                raise InvalidCommandError("Utilisation en phase d'annonce : "
                                          "`!p <valeur> <atout>`")
            async with table.lock:
                await table.bet(ctx, value, color)
        else:
            if len(args) == 0:
                value, color = None, None
            elif len(args) == 1:
                [value] = args
                color = None
            elif len(args) == 2:
                value, color = args
            else:
                raise InvalidCommandError("Utilisation :\n"
                                          "- `!p` pour jouer une carte au hasard\n"
                                          "- `!p <valeur>` pour jouer sans préciser la couleur\n"
                                          "- `!p <valeur> <couleur>`")

            async with table.lock:
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
        async with table.lock:
            await table.reset()
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command()
async def replay(ctx):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        async with table.lock:
            await table.reset(replay=True)
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

    async with table.lock:
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

    try:
        await table.add_spectator(ctx.author)
    except Exception as e:
        await handleGenericError(e, ctx.channel)

    await update_tables(ctx.guild)


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

    try:
        await table.remove_spectator(ctx.author)
    except Exception as e:
        await handleGenericError(e, ctx.channel)

    await update_tables(ctx.guild)


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
        async with table.lock:
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
            txt += " | ".join([p.mention for p in table.all_players])
            if table.spectators:
                txt += "\n   Spectateurices : "
                txt += " , ".join([s.mention for s in table.spectators])
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


@bot.command(aliases=["clear"])
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

    async with table.lock:
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
        async with table.lock:
            await table.surrender(ctx.author)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command()
async def hand(ctx):
    global tables
    await delete_message(ctx.message)

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await invalidChannelMessage(ctx.channel)
        return

    try:
        async with table.lock:
            await table.print_initial_hand(ctx.author)
    except Exception as e:
        await handleGenericError(e, ctx.channel)


@bot.command()
async def dispo(ctx, time="1h"):
    await delete_message(ctx.message)

    # Parse the time
    try:
        parsed = parser.parse(time)
        h = parsed.hour
        m = parsed.minute
        s = parsed.second
        s += 3600*h + 60*m
    except Exception:
        await handleGenericError(InvalidActionError("Je n'ai pas compris la durée. Utilise `<heures>h<minutes>`."))
        return

    await is_dispo(ctx.author, ctx.guild, s)


@bot.command(name="pudispo")
async def not_dispo(ctx):
    await delete_message(ctx.message)
    await is_not_dispo(ctx.author, ctx.guild)


async def is_dispo(user, guild, time):
    global avail_timers
    # Adding the role
    role = discord.utils.find(lambda r: r.name == "Dispo", guild.roles)
    await user.add_roles(role)

    # Delay the role deletion
    loop = asyncio.get_event_loop()
    timer = loop.call_later(time, lambda: asyncio.ensure_future(
        user.remove_roles(role)))

    # Remember the timer, to delete it if needed
    avail_timers[user] = timer


async def is_not_dispo(user, guild):
    if user in avail_timers:
        avail_timers[user].cancel()

    role = discord.utils.find(lambda r: r.name == "Dispo", guild.roles)
    await user.remove_roles(role)


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
