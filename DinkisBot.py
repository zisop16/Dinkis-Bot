import discord
from discord.ext import commands
import os
from dotenv import load_dotenv, find_dotenv
import re
import json
import asyncio
import sys, traceback

from TicketSystem import *
from DataManager import *

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = commands.Bot(command_prefix='/', help_command=None, intents=intents, case_insensitive=True)

load_dotenv(find_dotenv())
BOT_TOKEN = os.getenv("TOKEN")
MONGO_PASS = os.getenv("MONGO_PASS")

manager = DataManager(MONGO_PASS)

@client.command(name="warn")
async def issue_warning(context, *args):
    pass

@client.command(name="ticket")
@commands.has_permissions(administrator=True)
async def create_ticket(context):
    await context.send(
        embed = discord.Embed(
            description="Press the button to create a new ticket."
        ),
        view = OpenTickets()
    )

url_regex = re.compile(r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})")

from AutoResponseConfig import auto_responses
@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.guild is None:
        user_id = message.author.id
        await send_anonymous_message(user_id, message)
        return
    # General Chat
    if message.channel.id == 1151789214439067678:
        # Roles who are allowed to send URLs in general
        allowed_roles = {
            1228166328083550258,
            1158581405408837674,
            1229278618325225553,
            1229283129395777649,
            1208385680837705729,
            1148335950984912976
        }
        allowed = False
        for role in message.author.roles:
            if role.id in allowed_roles:
                allowed = True
                break
        if not allowed and url_regex.search(message.content):
            await message.delete()
            return
    if message.content.startswith(client.command_prefix):
        await client.process_commands(message)
        return
    
    
    for regex, response in auto_responses.items():
        if regex.search(message.content):
            embed = discord.Embed(description=response, color=discord.Color.dark_blue())
            download_message: discord.Message = await message.reply(embed=embed)
            await asyncio.sleep(60)
            await download_message.delete()
            return
        
@client.event
async def on_ready():
    client.add_view(OpenTickets())
    client.add_view(CloseButton())
    client.add_view(TrashButton())
    await clean_tickets(client)
    print("mister dinkis is ready")

client.run(BOT_TOKEN)