import discord
from discord.ext import commands

from coinche import Coinche


# Load the bot token
TOKEN = ""
with open(".token", "r") as f:
    TOKEN = f.readline()

bot = commands.Bot(command_prefix="!")

tables = {}
tables_msg = None
INDEX_CHAN = "tables-actives"


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

    await ctx.message.delete()
    tables[channel.id] = Coinche(channel, vocal_channel, players)
    await update_tables(ctx.guild)
    await tables[channel.id].start()


@bot.command()
async def annonce(ctx, goal: int, trump: str):
    global tables
    try:
        table = tables[ctx.channel.id]
        await table.annonce(ctx, goal, trump)
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command()
async def bet(ctx, goal: str, trump: str):
    global tables

    # Find the table
    try:
        table = tables[ctx.channel.id]
    except KeyError:
        await ctx.message.delete()
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
            await ctx.message.delete()
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
        await ctx.message.delete()
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
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command(aliases=["akor"])
async def again(ctx):
    global tables
    try:
        table = tables[ctx.channel.id]
        await table.reset()
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command()
async def end(ctx):
    global tables
    try:
        table = tables[ctx.channel.id]
        chan = table.channel
        await table.vocal.delete()
        for p in table.hands_msg:
            await table.hands_msg[p].delete()
        del tables[ctx.channel.id]
        await chan.send("Cloture de la table. Merci d'avoir joué !", delete_after=5)
        await chan.delete()
        await update_tables(ctx.guild)
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...", delete_after=5)


@bot.command()
async def spectate(ctx, id: int):
    global tables
    try:
        table = tables[id]
        await table.channel.set_permissions(ctx.author, read_messages=True)
        await table.vocal.set_permissions(ctx.author, connect=True)
        await table.channel.send("{} a rejoint en tant que spectateurice !".format(ctx.author.mention))
        await ctx.message.delete()
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Je reconnais pas l'id de la table", delete_after=5)


async def update_tables(guild):
    global tables
    global tables_msg
    txt = "__**Tables actives : **__"
    for id in tables:
        table = tables[id]
        txt += "\n - [{}] : ".format(str(id))
        txt += " | ".join([p.mention for p in table.players])

    if tables_msg is None:
        chan = discord.utils.find(
            lambda c: c.name == INDEX_CHAN, guild.channels)
        tables_msg = await chan.send(txt)
    else:
        await tables_msg.edit(content=txt)


bot.run(TOKEN)
