import discord
import asyncio
import discord.ext.commands
from discord.ui import Button, button, View

import discord.ext

open_tickets_category = 1232831284909445200
# Maps userIDs with open tickets to the channel of their ticket
open_tickets = {}
# List of user_ids with open anonymous reports
# The bot will poll messages from the DMs of these users to upload to their ticket channel
anonymous_reports = set()
anonymous_report_id = 0
# List of user_ids with open staff applications
staff_applications = {}

# Removes all open tickets which were left open the last time the bot was shut down
async def clean_tickets(client: discord.ext.commands.Bot):
    open_tickets = discord.utils.get(client.guilds[0].categories, id=open_tickets_category)
    deletions = [channel.delete() for channel in open_tickets.channels]
    for deletion in deletions:
        await deletion

async def send_anonymous_message(user_id: int, message: discord.Message):
    if not user_id in anonymous_reports:
        return False
    channel: discord.TextChannel = open_tickets[user_id][0]
    await channel.send(content=f"Anonymous User: {message.content}")
    return True

class OpenTickets(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @button(label="Report a player",style=discord.ButtonStyle.blurple, emoji="🕵️",custom_id="player_report")
    async def report(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id in open_tickets:
            channel = open_tickets[interaction.user.id][0]
            await interaction.followup.send(f"You already have a ticket in {channel.mention}", ephemeral=True)
            return
        
        await interaction.followup.send(
            embed= discord.Embed(
                description= "Please specify whether you would like your report to remain anonymous from staff",
                color = discord.Color.dark_blue()
            ),
            view = AnonymousReportPrompt(),
            ephemeral = True
        )

    @button(label="General Help",style=discord.ButtonStyle.blurple, emoji="⁉️",custom_id="general_help")
    async def general_help(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id in open_tickets:
            channel: discord.TextChannel = open_tickets[interaction.user.id][0]
            await interaction.followup.send(f"You already have a ticket in {channel.mention}", ephemeral=True)
            return
        
        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=open_tickets_category)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages = True, send_messages=True),
        }
        channel = await category.create_text_channel(
            name=interaction.user.display_name,
            overwrites=overwrites
        )

        close_ticket_message = await channel.send(
            embed=discord.Embed(
                title="General help ticket created",
                description="Please provide your question in whatever detail is necessary, and a moderator will answer shortly",
                color = discord.Color.green()
            ),
            view = CloseButton()
        )
        open_tickets[interaction.user.id] = channel, close_ticket_message

        await interaction.followup.send(
            embed= discord.Embed(
                description = f"Created your question ticket in {channel.mention}",
                color = discord.Color.blurple()
            ),
            ephemeral=True
        )
        
        
    @button(label="Apply for Staff",style=discord.ButtonStyle.blurple, emoji="📋",custom_id="apply_staff")
    async def apply(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id in staff_applications:
            channel = staff_applications[interaction.user.id]
            await interaction.followup.send(
                embed= discord.Embed(
                    description = f"You already have an ongoing staff application in {channel.mention}",
                    color = discord.Color.blurple()
                ),
                ephemeral=True
            )
            return
        apply_channel_id = 1232855364173565992
        channel = interaction.guild.get_channel(apply_channel_id)
        interaction.user.mention
        thread: discord.Thread = await channel.create_thread(name=f"Staff application of {interaction.user.display_name}", content="Thread")
        staff_applications.add(interaction.user.id)

    
    @button(label="Mod Suggestion",style=discord.ButtonStyle.blurple, emoji="🧐",custom_id="mod_suggest")
    async def suggest(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

    @button(label="Ask a Question",style=discord.ButtonStyle.blurple, emoji="🥪",custom_id="questions")
    async def ask_question(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        
class AnonymousReportPrompt(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Report Anonymously", style=discord.ButtonStyle.blurple, custom_id="anonymous_report", emoji="🎭")
    async def anonymous_report(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id in open_tickets:
            channel: discord.TextChannel = open_tickets[interaction.user.id][0]
            await interaction.followup.send(f"You already have a ticket in {channel.mention}", ephemeral=True)
            return
        
        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=open_tickets_category)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        }
        channel = await category.create_text_channel(
            name=f"Anonymous Report #{anonymous_report_id}",
            overwrites=overwrites
        )
        user_ticket_message = interaction.user.send(embed=discord.Embed(
                title="Player report ticket created",
                description="""1. What is the username of the player you are reporting?
2. What are you reporting them for?
3. Do you have evidence for your report?
Note: All messages you send to me until this ticket is closed will be given to the admin team,
But your identity will not be disclosed.""",
                color = discord.Color.green()
            ),
            view = CloseButton()
        )
        close_ticket_message = channel.send(
            embed=discord.Embed(
                title="Player report ticket created",
                description="""1. What is the username of the player you are reporting?
2. What are you reporting them for?
3. Do you have evidence for your report?
Note: All messages you send to me until this ticket is closed will be given to the admin team,
But your identity will not be disclosed.""",
                color = discord.Color.green()
            ),
            view = CloseButton()
        )
        await user_ticket_message
        await close_ticket_message

        anonymous_reports.add(interaction.user.id)
        open_tickets[interaction.user.id] = channel, close_ticket_message

        await interaction.followup.send(
            embed= discord.Embed(
                description = f"Your report ticket has been created. I will message you shortly for information.",
                color = discord.Color.blurple()
            ),
            ephemeral=True
        )
        

    @button(label="Standard Report", style=discord.ButtonStyle.blurple, custom_id="standard_report", emoji="🐼")
    async def standard_report(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id in open_tickets:
            channel: discord.TextChannel = open_tickets[interaction.user.id][0]
            await interaction.followup.send(f"You already have a ticket in {channel.mention}", ephemeral=True)
            return

        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=open_tickets_category)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages = True, send_messages=True),
        }
        channel = await category.create_text_channel(
            name=interaction.user.display_name,
            overwrites=overwrites
        )

        close_ticket_message = await channel.send(
            embed=discord.Embed(
                title="Player report ticket created",
                description="""1. What is the username of the player you are reporting?
2. What are you reporting them for?
3. Do you have evidence for your report?""",
                color = discord.Color.green()
            ),
            view = CloseButton()
        )
        open_tickets[interaction.user.id] = channel, close_ticket_message

        await interaction.followup.send(
            embed= discord.Embed(
                description = f"Created your report ticket in {channel.mention}",
                color = discord.Color.blurple()
            ),
            ephemeral=True
        )

class CloseButton(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @button(label="Close the ticket",style=discord.ButtonStyle.red,custom_id="closeticket",emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        closed_tickets_channel = 1232831690863546418
        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id = closed_tickets_channel)
        # moderator_role : discord.Role = interaction.guild.get_role(798882014022860811)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            # moderator_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            # interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        target_channel = open_tickets[interaction.user.id][0]
        await target_channel.edit(category=category, overwrites=overwrites)
        await target_channel.send(
            embed= discord.Embed(
                description= f"Ticket Closed for {interaction.user.display_name}",
                color = discord.Color.red()
            ),
            view = TrashButton()
        )
        close_ticket_message = open_tickets[interaction.user.id][1]
        del open_tickets[interaction.user.id]
        anonymous_reports.remove(interaction.user.id)

        await close_ticket_message.delete()

class TrashButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Delete the ticket", style=discord.ButtonStyle.red, emoji="🚮", custom_id="trash")
    async def trash(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()

        await interaction.channel.delete()