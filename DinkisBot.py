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
import DataManager

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = commands.Bot(intents=intents, command_prefix='/')

load_dotenv(find_dotenv())
BOT_TOKEN = os.getenv("TOKEN")
MONGO_PASS = os.getenv("MONGO_PASS")

DataManager.manager = DataManager.DataManager(MONGO_PASS)

@client.tree.command(name="warn")
@app_commands.describe(user="User to warn")
@app_commands.checks.has_permissions(moderate_members=True)
async def issue_warning(interaction: discord.Interaction, user: discord.Member):
    """
    Warn a user, keeping a running count over multiple warnings
    """
    DataManager.manager.add_warning(user.id)
    warnings = DataManager.manager.get_warnings(user.id)
    await interaction.response.send_message(embed = discord.Embed(
        description=f"User: {user.mention} now has {warnings} warning{'' if warnings == 1 else 's total.'}"
    ))

@client.tree.command(name="unwarn")
@app_commands.describe(user="User to unwarn")
@app_commands.checks.has_permissions(moderate_members=True)
async def remove_warning(interaction: discord.Interaction, user: discord.Member):
    """
    Unwarn a user, removing 1 warning from their count
    """
    DataManager.manager.remove_warning(user.id)
    warnings = DataManager.manager.get_warnings(user.id)
    await interaction.response.send_message(embed = discord.Embed(
        description=f"User: {user.mention} now has {warnings} warning{'' if warnings == 1 else 's total.'}"
    ))

@client.tree.command(name="resetwarn")
@app_commands.describe(user="User to reset warnings for")
@app_commands.checks.has_permissions(moderate_members=True)
async def remove_warning(interaction: discord.Interaction, user: discord.Member):
    """
    Sets a user's warnings count to 0
    """
    DataManager.manager.reset_warnings(user.id)
    await interaction.response.send_message(embed = discord.Embed(
        description=f"User: {user.mention} now has 0 warnings."
    ))


@client.tree.command(name="announce")
@app_commands.describe(title="Title of Announcement", pings="Whether to ping the pings role", server_status="Whether to ping server status role", message="Message of announcement")
@app_commands.checks.has_permissions(moderate_members=True)
async def create_announcement(interaction: discord.Interaction, title: str, pings: bool, server_status: bool, message: str):
    """
    Creates an announcement in the announcements channel
    """
    await interaction.response.defer(ephemeral=True)
    announcements_channel = interaction.guild.get_channel(NationsIDs.announcements_channel)
    pings_role = interaction.guild.get_role(NationsIDs.pings_role)
    server_status_role = interaction.guild.get_role(NationsIDs.server_status_role)
    message = bytes(message, "utf-8").decode("unicode_escape")
    message = f"{pings_role.mention if pings else ''} {server_status_role.mention if server_status else ''}\n{message}"
    await announcements_channel.send(embed=discord.Embed(
        title=title,
        description=message
    ))
    
    await interaction.followup.send(embed = discord.Embed(
        description=f"Created your {title} announcement in channel: {announcements_channel.mention}"
    ))

@client.tree.command(name="formban")
@app_commands.describe(user="User to ban from using bot forms")
@app_commands.checks.has_permissions(manage_roles=True)
async def form_ban(interaction: discord.Interaction, user: discord.Member):
    """
    Bans a user from accessing bot forms
    """
    await interaction.response.defer(ephemeral=True)

    server = interaction.guild
    form_ban = server.get_role(NationsIDs.form_ban_role)
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
    form_ban = server.get_role(NationsIDs.form_ban_role)
    await user.remove_roles(form_ban)
    await interaction.followup.send(embed = discord.Embed(
            description=f"User: {user.mention} was unbanned from forms"
    ))


    

@client.tree.command(name="ticket")
@app_commands.checks.has_permissions(administrator=True)
async def create_ticket(interaction: discord.Interaction):
    """
    Open a ticket with mister dinkis to begin various forms
    """
    banned = await check_form_banned(interaction)
    if banned:
        return

    await interaction.response.send_message(
        embed = discord.Embed(
            description="Press the button to create a new ticket."
        ),
        view = OpenTickets()
    )

@form_ban.error
@form_unban.error
@issue_warning.error
@create_ticket.error
@create_announcement.error
async def permissions_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(
            description=str(error)
        ))

url_regex = re.compile(r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})")

async def get_thread_author(thread: discord.Thread):
    if thread.starter_message is not None:
        start_message = thread.starter_message
    else:
        start_message = await thread.fetch_message(thread.id)
    thread_author = start_message.author
    return thread_author

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
    
    if type(message.channel) == discord.Thread:
        thread_channel = message.channel.parent
        # LFT thread
        if thread_channel.id == NationsIDs.lft_channel:
            thread = message.channel
            start_message = await thread.fetch_message(thread.id)
            thread_author = start_message.author
            if message.author != thread_author:
                deletion = message.delete()
                reason = message.author.send(content="You are not allowed to write messages in other users' LFT threads.")
                await deletion, await reason
                return
            # New thread has been created
            if message == start_message:
                all_threads = thread_channel.threads
                count = 0
                authors = [get_thread_author(thread) for thread in all_threads]
                for author in authors:
                    author = await author
                    if author == message.author:
                        count += 1
                    if count == 2:
                        break
                # User has posted a second LFT thread
                if count == 2:
                    deletion = thread.delete()
                    reason = message.author.send(content="You are not allowed to post more than one LFT thread.")
                    await deletion, await reason
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
    clean = clean_tickets(client)
    sync = client.tree.sync()
    await clean, await sync
    print("mister dinkis is ready")

client.run(BOT_TOKEN)