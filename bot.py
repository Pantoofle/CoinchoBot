import sys
import discord
from discord.ext import commands

from coinche import Coinche
from carte import Carte


# Load the bot token
TOKEN = ""
with open(".token", "r") as f:
    TOKEN = f.readline()

bot = commands.Bot(command_prefix="!")

tables = {}

@bot.command()
async def start(ctx, p2: discord.Member, p3: discord.Member, p4: discord.Member):
    players = [ctx.author, p2, p3, p4]
    await ctx.send("Starting a game with " + ", ".join([p.mention for p in players]), delete_after = 10)

    guild = ctx.guild
    base = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False)
    }


    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        players[0] : discord.PermissionOverwrite(read_messages=True),
        players[1] : discord.PermissionOverwrite(read_messages=True),
        players[2] : discord.PermissionOverwrite(read_messages=True),
        players[3] : discord.PermissionOverwrite(read_messages=True)
    }

    category = discord.utils.find(lambda cat: cat.name == "Tables de Coinche", ctx.guild.categories)
    if not category:
        category = await ctx.guild.create_category("Tables de Coinche", overwrites=base)

    channel = await ctx.guild.create_text_channel(
        name="table-coinche",
        category=category,
        overwrites=overwrites
    )

    await ctx.message.delete()
    tables[channel.id] = Coinche(channel, players)
    await tables[channel.id].start()

@bot.command()
async def annonce(ctx, goal: int, trump: str):
    try:
        table = tables[ctx.channel.id]
        await table.annonce(ctx, goal, trump)
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...")

@bot.command()
async def bet(ctx, goal: int, trump: str):
    try:
        table = tables[ctx.channel.id]
        await table.bet(ctx, goal, trump)
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...")

@bot.command(name="p")
async def play(ctx, value, *args):
    color = args[-1]
    try:
        table = tables[ctx.channel.id]
        await table.play(ctx, value, color)
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...")

@bot.command()
async def again(ctx):
    try:
        table = tables[ctx.channel.id]
        await table.reset()
    except KeyError:
        await ctx.message.delete()
        await ctx.channel.send("Tu peux pas faire ça hors d'un channel de coinche...")



bot.run(TOKEN)
