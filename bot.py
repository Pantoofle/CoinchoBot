import sys
import discord
from discord.ext import commands

import coinche


# Load the bot token
TOKEN = ""
with open(".token", "r") as f:
    TOKEN = f.readline()

bot = commands.Bot(command_prefix="!coinche ")

tables = []

@bot.command()
async def start(ctx, p2: discord.Member, p3: discord.Member, p4: discord.Member):
    players = [ctx.author, p2, p3, p4]
    # print(players)
    await ctx.send("Starting a game with " + ", ".join([p.mention for p in players]))

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

    await channel.send("Hey, ça se passe ici ! " + ", ".join([p.mention for p in players]))

    tables.append(Coinche())


bot.run(TOKEN)
