import discord

async def append_line(msg, line):
    content = msg.content
    content += "\n" + line
    await msg.edit(content = content)

async def remove_last_line(msg):
    content = msg.content.split("\n")[:-1]
    await msg.edit(content = content)

