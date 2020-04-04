import discord
from discord.ext import commands
import random
from utils import delete_message

from coinche import Coinche


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
    try:
        table = tables[ctx.channel.id]
        await table.annonce(ctx, goal, trump)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command()
async def bet(ctx, goal: str, trump: str):
    global tables

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)
        return

    # Parse the goal
    capot = (goal == "capot")
    generale = (goal == "generale")
    if capot or generale:
        goal = 182
        if generale:
            goal += 1
    else:
        try:
            goal = int(goal)
        except ValueError:
            await delete_message(ctx.message)
            await ctx.channel.send("J'ai pas compris ton annonce...", delete_after=5)
            return

    # Send the goal
    await table.bet(ctx, goal, trump, capot=capot, generale=generale)


@bot.command(name="pass", aliases=["nik"])
async def pass_annonce(ctx):
    global tables
    try:
        table = tables[ctx.channel.id]
        await table.bet(ctx, 0, None)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command(name="p")
async def play(ctx, value, *args):
    global tables
    color = args[-1]
    try:
        table = tables[ctx.channel.id]
        # If we are un bet phase, consider !p as a bet
        if table.bet_phase:
            await bet(ctx, value, color)
            return
        await table.play(ctx, value, color)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command(aliases=["akor"])
async def again(ctx):
    global tables
    try:
        table = tables[ctx.channel.id]
        await table.reset()
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command()
async def end(ctx):
    global tables
    try:
        table = tables[ctx.channel.id]
        chan = table.channel
        await delete_message(table.vocal)
        for p in table.hands_msg:
            await delete_message(table.hands_msg[p])
        del tables[ctx.channel.id]
        await chan.send("Cloture de la table. Merci d'avoir joué !", delete_after=5)
        await delete_message(chan)
        await update_tables(ctx.guild)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command()
async def spectate(ctx, index: int):
    global tables
    try:
        id = index_to_id[index]
        table = tables[id]
        await table.channel.set_permissions(ctx.author, read_messages=True)
        await table.vocal.set_permissions(ctx.author, view_channel=True)
        await table.channel.send("{} a rejoint en tant que spectateurice !".format(ctx.author.mention))
        await delete_message(ctx.message)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Je reconnais pas l'id de la table", delete_after=5)


@bot.command()
async def leave(ctx):
    global tables
    try:
        table = tables[ctx.channel.id]
        await table.channel.set_permissions(ctx.author, read_messages=False)
        await table.vocal.set_permissions(ctx.author, view_channel=False)
        await table.channel.send("{} n'est plus spectateurice !".format(ctx.author.mention))
        await delete_message(ctx.message)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Je peux pas faire ça hors d'un chan de coinche", delete_after=5)


@bot.command()
async def swap(ctx, target: discord.Member):
    global tables
    try:
        table = tables[ctx.channel.id]
        await table.swap(ctx.author, target)
        await delete_message(ctx.message)
        await update_tables(ctx.guild)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Je peux pas faire ça hors d'un chan de coinche", delete_after=5)


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
    try:
        table = tables[ctx.channel.id]
        # Delete all messages not from CoinchoBot
        async for m in table.channel.history():
            if m.author != bot.user:
                await delete_message(m)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command(aliases=["nomore"])
async def surrender(ctx):
    global tables
    try:
        table = tables[ctx.channel.id]
        await table.surrender(ctx.author)
    except KeyError:
        await delete_message(ctx.message)
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


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
