import discord
import asyncio
import discord.ext.commands
from discord.ui import Button, button, View
import re

import discord.ext
import NationsIDs

# Maps userIDs with open tickets to the channel of their ticket
open_tickets = {}
# List of user_ids with open anonymous reports
# The bot will poll messages from the DMs of these users to upload to their ticket channel
anonymous_reports = set()
anonymous_report_id = 0

# Stores channel of all threads with default names like "dog man's mod request"
# We will repeatedly search through these threads looking for renames, then remove them from the set
default_mod_requests = set()
default_questions = set()


async def check_form_banned(interaction: discord.Interaction):
    member = interaction.user
    form_ban_role = interaction.guild.get_role(NationsIDs.form_ban_role)
    banned = form_ban_role in member.roles

    if banned:
        await interaction.followup.send(
                embed = discord.Embed(
                    description="You are currently banned from accessing forms."
            ), ephemeral=True)
    
    return banned

# Removes all open tickets which were left open the last time the bot was shut down
async def clean_tickets(client: discord.ext.commands.Bot):
    open_tickets = discord.utils.get(client.guilds[0].categories, id=NationsIDs.open_tickets_category)
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
        banned = await check_form_banned(interaction)
        if banned:
            return

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
        banned = await check_form_banned(interaction)
        if banned:
            return
        

        if interaction.user.id in open_tickets:
            channel: discord.TextChannel = open_tickets[interaction.user.id][0]
            await interaction.followup.send(f"You already have a ticket in {channel.mention}", ephemeral=True)
            return
        
        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=NationsIDs.open_tickets_category)
        all_perms = discord.PermissionOverwrite(read_messages = True, send_messages = True, manage_messages = True)
        moderator_role = interaction.guild.get_role(NationsIDs.moderator_role)
        admin_role = interaction.guild.get_role(NationsIDs.admin_role)
        overwrites = {
            moderator_role: all_perms,
            admin_role: all_perms,
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages = True, send_messages=True),
        }
        channel = await category.create_text_channel(
            name=interaction.user.display_name,
            overwrites=overwrites
        )

        open_ticket_message = await channel.send(
            content=f"{moderator_role.mention}",
            embed=discord.Embed(
                title="General help ticket created",
                description="Please provide your question in whatever detail is necessary, and a moderator will answer shortly",
                color = discord.Color.green()
            ),
            view = CloseButton()
        )
        open_tickets[interaction.user.id] = channel, open_ticket_message

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
        banned = await check_form_banned(interaction)
        if banned:
            return
        """
        if interaction.user.id in staff_applications:
            channel = staff_applications[interaction.user.id]
            await interaction.followup.send(
                embed= discord.Embed(
                    description = f"You already have an ongoing staff application",
                    color = discord.Color.blurple()
                ),
                ephemeral=True
            )
            return
        """
        
        footer="""The title of the post will be based on your response to part A, so please make sure to put your name like A. Dinkis_Brother23
Only the most recent message you have sent before submitting the application will be read, so contain your entire application within the last message you send me before pressing the submit button."""
        questions = """a. What is your minecraft username?
b. How old are you?
c. Where did you find us?
d. What position are you applying for?
e. What past experiences do you have?
f. Do you have a portfolio?
g. How long ago did you join the server?
h. How many hours per week can you commit to the server?
i. Do you understand abuse of your position will result in a premanent ban from the server with no chance of appeal?
j. Please provide any additional information you will be useful in the application process here.
"""
        application_embed = discord.Embed(
                title="Staff Application Information",
                color = discord.Color.green()
            )
        application_embed.add_field(name="Questions", value=questions)
        application_embed.set_footer(text=footer)
        user_ticket_message = await interaction.user.send(embed=application_embed, view = SubmitButton(interaction.guild, SubmitButton.STAFF_APPLICATION))
        
        await interaction.followup.send(
            embed= discord.Embed(
                description = f"I've messaged you a prompt to begin your staff application",
                color = discord.Color.blurple()
            ),
            ephemeral=True
        )

    
    @button(label="Mod Suggestion",style=discord.ButtonStyle.blurple, emoji="🧐",custom_id="mod_suggest")
    async def suggest(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        banned = await check_form_banned(interaction)
        if banned:
            return
        
        footer="""The title of the post will be based on your response to part A, so please make sure to put your mod name like A. Create Some Spaghetti
Only the most recent message you have sent before submitting the suggestion will be read, so contain your entire suggestion within the last message you send me before pressing the submit button."""
        
        questions = """A. What is the name of the mod?
B. Please list all versions of minecraft the mod is available in
C. Please give a link to the mod
D. Why do you think the mod should be added?
"""
        suggestion_embed = discord.Embed(
                title="Mod Suggestion Template",
                color = discord.Color.green()
            )
        suggestion_embed.add_field(name="Questions", value=questions)
        suggestion_embed.set_footer(text=footer)
        user_ticket_message = await interaction.user.send(embed=suggestion_embed, view = SubmitButton(interaction.guild, SubmitButton.MOD_SUGGESTION))

        await interaction.followup.send(
            embed= discord.Embed(
                description = f"I've messaged you a prompt regarding your mod suggestion",
                color = discord.Color.blurple()
            ),
            ephemeral=True
        )

    @button(label="Ask a Question",style=discord.ButtonStyle.blurple, emoji="🥪",custom_id="questions")
    async def ask_question(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        banned = await check_form_banned(interaction)
        if banned:
            return
        
        questions = "A. What is your question?\nB. Provide any further elaboration if necessary"
        footer="""The title of the post will be based on your response to part A, so please make sure to put your question like A. What is spaghetti?
Only the most recent message you have sent before submitting the suggestion will be read, so contain your entire suggestion within the last message you send me before pressing the submit button."""
        question_embed = embed=discord.Embed(
            title="Question Template",
            color = discord.Color.green()
        )
        question_embed.add_field(name="Questions", value=questions)
        question_embed.set_footer(text=footer)

        user_ticket_message = await interaction.user.send(embed=question_embed, view=SubmitButton(interaction.guild, SubmitButton.QUESTION_THREAD))

        await interaction.followup.send(
            embed= discord.Embed(
                description = f"I've sent you a prompt regarding the details of your question.",
                color = discord.Color.blurple()
            ),
            ephemeral=True
        )

class SubmitButtonException(Exception):
    pass
class SubmitButton(View):
    username_regex = re.compile(r"a[.|:]?[\s]?(\S*)", re.IGNORECASE)
    part_a_regex = re.compile(r"a[.|:]?[\s]?(.*)(?:\n|$)", re.IGNORECASE)

    STAFF_APPLICATION = 0
    QUESTION_THREAD = 1
    MOD_SUGGESTION = 2

    def __init__(self, server: discord.Guild, type):
        super().__init__(timeout=None)
        match(type):
            case SubmitButton.STAFF_APPLICATION:
                self.channel_id = NationsIDs.staff_application
            case SubmitButton.QUESTION_THREAD:
                self.channel_id = NationsIDs.question_channel
            case SubmitButton.MOD_SUGGESTION:
                self.channel_id = NationsIDs.suggestion_channel
            case _:
                raise SubmitButtonException(f"Attempted to create a submit button of type: {type}")
        self.server = server
        self.type = type

    @button(label="Submit", style=discord.ButtonStyle.blurple, custom_id="submit_button", emoji="✅")
    async def submit_form(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        direct_message_channel: discord.DMChannel = interaction.channel
        recent_message = [message async for message in direct_message_channel.history(limit=1)][0]
        if recent_message.author != interaction.user:
            await interaction.followup.send(
                embed= discord.Embed(
                    description = f"Please respond to the application before submitting.",
                    color = discord.Color.blurple()
                ),
                ephemeral=True
            )
            return
        
        thread_channel = self.server.get_channel(self.channel_id)

        match(self.type):
            case SubmitButton.STAFF_APPLICATION:
                match = SubmitButton.username_regex.match(recent_message.content)
                if match is None:
                    await interaction.followup.send(
                        embed= discord.Embed(
                            description = f"I couldn't find your username in your most recent submission. Please reformat and try again.",
                            color = discord.Color.blurple()
                        ),
                        ephemeral=True
                    )
                    return
                username = match.groups()[0]
                await (await interaction.original_response()).delete()
                await thread_channel.create_thread(
                    name=f"{username}'s Application for Staff",
                    content=f"{recent_message.content}\n{username}'s discord: {interaction.user.mention}",
                )
                
                
            case SubmitButton.MOD_SUGGESTION:
                match = SubmitButton.part_a_regex.match(recent_message.content)
                if match is None:
                    await interaction.followup.send(
                        embed= discord.Embed(
                            description = f"I couldn't find the mod name in your most recent submission. Please reformat and try again.",
                            color = discord.Color.blurple()
                        ),
                        ephemeral=True
                    )
                    return
                mod_name = match.groups()[0]
                def strip(string: str):
                    return string.lower().replace(' ', '')
                stripped = strip(mod_name)
                duplicate = None
                for thread in thread_channel.threads:
                    if strip(thread.name) == stripped:
                        duplicate = thread
                        break
                
                if duplicate:
                    await interaction.followup.send(
                        embed=discord.Embed(
                            description=f"That mod has already been suggested: {duplicate.mention}"
                        ), ephemeral=True
                    )
                    return
                await (await interaction.original_response()).delete()
                creation = await thread_channel.create_thread(
                    name=mod_name,
                    content = f"{recent_message.content}\nSuggested by: {interaction.user.mention}"
                )
                await creation.message.add_reaction('✅')
                await creation.message.add_reaction('❌')

            case SubmitButton.QUESTION_THREAD:
                match = SubmitButton.part_a_regex.match(recent_message.content)
                if match is None:
                    await interaction.followup.send(
                        embed= discord.Embed(
                            description = f"I couldn't find the question in your most recent submission. Please reformat and try again.",
                            color = discord.Color.blurple()
                        ),
                        ephemeral=True
                    )
                    return
                question = match.groups()[0]
                await thread_channel.create_thread(
                    name=question,
                    content = f"{recent_message.content}\nAsked by: {interaction.user.mention}"
                )
                await (await interaction.original_response()).delete()

        await interaction.followup.send(embed=discord.Embed(
            description="I've posted your thread in the server",
        ), ephemeral=True)
        
                
        # await thread_channel.create_thread

        
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
        
        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=NationsIDs.open_tickets_category)
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
        # Moderators cannot see anonymous reports
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

        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=NationsIDs.open_tickets_category)
        all_perms = discord.PermissionOverwrite(read_messages = True, send_messages = True, manage_messages = True)
        moderator_role = interaction.guild.get_role(NationsIDs.moderator_role)
        admin_role = interaction.guild.get_role(NationsIDs.admin_role)
        overwrites = {
            moderator_role: all_perms,
            admin_role: all_perms,
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages = True, send_messages=True),
        }
        channel = await category.create_text_channel(
            name=interaction.user.display_name,
            overwrites=overwrites
        )

        close_ticket_message = await channel.send(
            content=f"{moderator_role.mention}",
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
        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id = NationsIDs.closed_tickets_category)
        all_perms = discord.PermissionOverwrite(read_messages = True, send_messages = True, manage_messages = True)
        moderator_role = interaction.guild.get_role(NationsIDs.moderator_role)
        admin_role = interaction.guild.get_role(NationsIDs.admin_role)
        overwrites = {
            moderator_role: all_perms,
            admin_role: all_perms,
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages = True, send_messages=True),
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
        anonymous_reports.discard(interaction.user.id)

        await close_ticket_message.delete()

class TrashButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Delete the ticket", style=discord.ButtonStyle.red, emoji="🚮", custom_id="trash")
    async def trash(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()

        await interaction.channel.delete()