import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv, find_dotenv
import re
import json
import asyncio
import sys, traceback

import NationsIDs
from TicketSystem import *
from DataManager import *

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = commands.Bot(intents=intents, command_prefix='/')

load_dotenv(find_dotenv())
BOT_TOKEN = os.getenv("TOKEN")
MONGO_PASS = os.getenv("MONGO_PASS")

manager = DataManager(MONGO_PASS)

@client.tree.command(name="warn")
async def issue_warning(interaction):
    pass

@client.tree.command(name="formban")
@app_commands.describe(user="User to ban from using bot forms")
@app_commands.checks.has_permissions(manage_roles=True)
async def form_ban(interaction: discord.Interaction, user: discord.Member):
    """
    Bans a user from accessing bot forms
    """
    await interaction.response.defer(ephemeral=True)
    
    server = interaction.guild
    form_ban = server.get_role(form_ban_id)
    await user.add_roles(form_ban)
    await interaction.followup.send(embed = discord.Embed(
            description=f"User: {user.mention} was form banned"
    ))

@client.tree.command(name="formunban")
@app_commands.describe(user="User to unban from using bot forms")
@app_commands.checks.has_permissions(manage_roles=True)
async def form_unban(interaction: discord.Interaction, user: discord.Member):
    """
    Unbans a user from accessing bot forms
    """
    await interaction.response.defer(ephemeral=True)
    server = interaction.guild
    form_ban = server.get_role(form_ban_id)
    await user.remove_roles(form_ban)
    await interaction.followup.send(embed = discord.Embed(
            description=f"User: {user.mention} was unbanned from forms"
    ))

@form_ban.error
@form_unban.error
async def ban_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(
            description=str(error)
        ))
    

@client.tree.command(name="ticket")
async def create_ticket(interaction: discord.Interaction):
    """
    Open a ticket with mister dinkis to begin various forms
    """
    
    await interaction.response.defer(ephemeral=True)
    banned = await check_form_banned(interaction)
    if banned:
        return

    await interaction.followup.send(
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
    if message.channel.id == NationsIDs.general_channel:
        
        allowed = False
        for role in message.author.roles:
            if role.id in NationsIDs.general_url_roles:
                allowed = True
                break
        if not allowed and url_regex.search(message.content):
            await message.delete()
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
    sync = await client.tree.sync()

client.run(BOT_TOKEN)