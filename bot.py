import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from discord import Member, Role, app_commands
from discord.ext.commands import has_permissions, MissingPermissions
from typing import Optional
import random
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Enable all intents for testing
intents = discord.Intents.all()

# Initialize bot with intents
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    activity=discord.Activity(type=discord.ActivityType.watching, name='your server')
)
tree = bot.tree

# Store active giveaways
giveaways = {}

@bot.event
async def on_ready():
    print('=' * 50)
    print(f'Bot is ready! Logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f'Bot is in {len(bot.guilds)} guild(s):')
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')
    print('=' * 50)
    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing commands: {e}')
    check_giveaways.start()

@tree.command(name="giveaway", description="Start a new giveaway")
@app_commands.describe(
    duration="Duration of the giveaway (e.g., 30m, 1h, 2d, 1w)",
    winners="Number of winners",
    prize="Prize to be won",
    min_participants="Minimum number of participants required (default: 1)"
)
async def giveaway(interaction: discord.Interaction, duration: str, winners: int, prize: str, min_participants: int = 1):
    """Start a new giveaway with optional minimum participants"""
    # Parse duration (format: 1m, 1h, 1d, 1w)
    try:
        time_unit = duration[-1].lower()
        time_value = int(duration[:-1])
        
        if time_unit == 'm':
            end_time = datetime.utcnow() + timedelta(minutes=time_value)
        elif time_unit == 'h':
            end_time = datetime.utcnow() + timedelta(hours=time_value)
        elif time_unit == 'd':
            end_time = datetime.utcnow() + timedelta(days=time_value)
        elif time_unit == 'w':
            end_time = datetime.utcnow() + timedelta(weeks=time_value)
        else:
            await interaction.response.send_message("Invalid time unit. Use 'm' for minutes, 'h' for hours, 'd' for days, or 'w' for weeks.", ephemeral=True)
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"🎉 {prize}",
            description=f"React with 🎉 to enter!\nHosted by: {interaction.user.mention}\nEnds: {end_time.strftime('%Y-%m-%d %H:%M')} UTC\nWinners: {winners}",
            color=0x00ff00
        )
        
        # Send the giveaway message
        await interaction.response.send_message("🎉 **GIVEAWAY STARTED** 🎉", embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("🎉")
        
        # Store giveaway info
        giveaways[message.id] = {
            'channel_id': interaction.channel.id,
            'end_time': end_time,
            'prize': prize,
            'winners': winners,
            'host': interaction.user.id,
            'min_participants': min_participants,
            'message_id': message.id
        }
        
    except ValueError:
        await interaction.response.send_message("Invalid duration format. Use something like '1h', '1d', or '1w 1d'.", ephemeral=True)

async def check_and_end_giveaway(message_id, giveaway):
    """Helper function to check and end a single giveaway"""
    try:
        channel = bot.get_channel(giveaway['channel_id'])
        message = await channel.fetch_message(message_id)
        
        # Get all users who reacted with 🎉
        users = []
        for reaction in message.reactions:
            if str(reaction.emoji) == '🎉':
                async for user in reaction.users():
                    if not user.bot:
                        users.append(user)
        
        # Check minimum participants
        if len(users) < giveaway['min_participants']:
            # Check if we should extend the time (first time not meeting minimum)
            if not giveaway.get('extended'):
                # Extend the giveaway by 1 minute
                giveaway['end_time'] = datetime.utcnow() + timedelta(minutes=1)
                giveaway['extended'] = True
                
                # Update the embed to show extended time
                embed = message.embeds[0]
                embed.description = (
                    f"React with 🎉 to enter!\n"
                    f"Hosted by: <@{giveaway['host']}>\n"
                    f"Ends: {giveaway['end_time'].strftime('%Y-%m-%d %H:%M')} UTC (Extended by 1 minute)\n"
                    f"Winners: {giveaway['winners']}\n"
                    f"Minimum participants: {giveaway['min_participants']}"
                )
                await message.edit(embed=embed)
                await message.channel.send(
                    f"⚠️ Not enough participants for the giveaway of **{giveaway['prize']}**! "
                    f"Extended by 1 minute. Need {giveaway['min_participants'] - len(users)} more participants!"
                )
                return False  # Don't end the giveaway yet
            
            # If we already extended and still not enough participants
            await message.channel.send(
                f"❌ Giveaway for **{giveaway['prize']}** has ended!\n"
                f"**Not enough participants!** (Minimum {giveaway['min_participants']} required, got {len(users)})"
            )
            # Update the embed
            embed = message.embeds[0]
            embed.color = 0xff0000
            embed.description = (
                f"❌ **GIVEAWAY ENDED** ❌\n"
                f"Not enough participants! (Minimum {giveaway['min_participants']} required)\n"
                f"Prize: {giveaway['prize']}"
            )
            await message.edit(embed=embed)
            return True
            
        # If we have enough participants, proceed with selecting winners
        winners = random.sample(users, min(giveaway['winners'], len(users)))
        winners_mentions = ', '.join([winner.mention for winner in winners])
        
        # Update the embed
        embed = message.embeds[0]
        embed.color = 0xff0000
        embed.description = (
            f"🎉 **GIVEAWAY ENDED** 🎉\n"
            f"Winners: {winners_mentions}\n"
            f"Prize: {giveaway['prize']}\n"
            f"{len(users)} participants"
        )
        await message.edit(embed=embed)
        
        # Announce winners
        await message.reply(f"🎉 Congratulations {winners_mentions}! You won **{giveaway['prize']}**!")
        return True
        
    except Exception as e:
        print(f"Error in check_and_end_giveaway: {e}")
        return True  # If there's an error, remove the giveaway to prevent getting stuck

@tasks.loop(seconds=30)
async def check_giveaways():
    """Check for giveaways that have ended"""
    current_time = datetime.utcnow()
    to_remove = []
    
    for message_id, giveaway in list(giveaways.items()):
        if current_time >= giveaway['end_time']:
            should_remove = await check_and_end_giveaway(message_id, giveaway)
            if should_remove:
                to_remove.append(message_id)
    
    # Clean up ended giveaways
    for message_id in to_remove:
        giveaways.pop(message_id, None)

@tree.command(name="reroll", description="Reroll winners for a giveaway")
@app_commands.describe(
    message_id="ID of the giveaway message",
    winners="Number of winners to select (default: 1)"
)
@has_permissions(kick_members=True)
async def reroll(interaction: discord.Interaction, message_id: str, winners: int = 1):
    """Reroll winners for a giveaway"""
    try:
        # Convert message_id to integer and fetch the message
        message_id = int(message_id)
        message = await interaction.channel.fetch_message(message_id)
        
        # Get all users who reacted with 🎉
        users = []
        for reaction in message.reactions:
            if str(reaction.emoji) == '🎉':
                async for user in reaction.users():
                    if not user.bot:
                        users.append(user)
        
        if users:
            winners_list = random.sample(users, min(winners, len(users)))
            winners_mentions = ', '.join([winner.mention for winner in winners_list])
            await interaction.response.send_message(
                f"🎉 New winner(s): {winners_mentions}!",
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                "No valid participants found.",
                ephemeral=True
            )
            
    except ValueError:
        await interaction.response.send_message(
            "Please provide a valid message ID.",
            ephemeral=True
        )
    except discord.NotFound:
        await interaction.response.send_message(
            "Could not find the specified message.",
            ephemeral=False
        )
    except Exception as e:
        await interaction.response.send_message(
            f"An error occurred: {e}",
            ephemeral=False
        )

@tree.command(name="ban", description="Ban a member from the server")
@app_commands.describe(
    member="Member to ban",
    reason="Reason for the ban"
)
@has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    """Ban a member from the server"""
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(
            f'✅ {member.mention} has been banned. Reason: {reason or "No reason provided"}',
            ephemeral=False
        )
    except Exception as e:
        await interaction.response.send_message(
            f'❌ Could not ban {member.mention}. Error: {e}',
            ephemeral=False
        )

@tree.command(name="kick", description="Kick a member from the server")
@app_commands.describe(
    member="Member to kick",
    reason="Reason for the kick"
)
@has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    """Kick a member from the server"""
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(
            f'👢 {member.mention} has been kicked. Reason: {reason or "No reason provided"}',
            ephemeral=False
        )
    except Exception as e:
        await interaction.response.send_message(
            f'❌ Could not kick {member.mention}. Error: {e}',
            ephemeral=False
        )

@tree.command(name="mute", description="This message will be visible to everyone")
@app_commands.describe(
    member="Member to mute (leave empty to mute yourself)",
    duration="Duration of the mute (e.g., 30m, 2h, 1d)",
    reason="Reason for the mute"
)
@has_permissions(kick_members=True)
async def mute(interaction: discord.Interaction, member: Optional[discord.Member] = None, duration: str = "1h", reason: Optional[str] = None):
    """This message will be visible to everyone"""
    try:
        # If no member specified, mute the command user
        if member is None:
            member = interaction.user
        # Find or create muted role
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        
        if not muted_role:
            # Create muted role if it doesn't exist
            muted_role = await interaction.guild.create_role(name="Muted")
            
            # Set permissions for the muted role
            for channel in interaction.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)
        
        # Parse duration (format: 1h, 1d, 1w)
        time_unit = duration[-1].lower()
        time_value = int(duration[:-1])
        
        if time_unit == 'm':
            mute_duration = timedelta(minutes=time_value)
        elif time_unit == 'h':
            mute_duration = timedelta(hours=time_value)
        elif time_unit == 'd':
            mute_duration = timedelta(days=time_value)
        else:
            await ctx.send("Invalid time unit. Use 'm' for minutes, 'h' for hours, or 'd' for days.")
            return
        
        # Add muted role to the member
        await member.add_roles(muted_role, reason=reason)
        
        # Send confirmation message
        await interaction.response.send_message(
            f'🔇 {member.mention} has been muted for {duration}. Reason: {reason or "No reason provided"}',
            ephemeral=False
        )
        
        # Schedule unmute
        await asyncio.sleep(mute_duration.total_seconds())
        if muted_role in member.roles:
            await member.remove_roles(muted_role)
            channel = interaction.channel
            await channel.send(f'🔊 {member.mention} has been automatically unmuted after {duration}.')
            
    except Exception as e:
        await interaction.response.send_message(
            f'❌ Could not mute {member.mention}. Error: {e}',
            ephemeral=False
        )

@tree.command(name="unmute", description="Unmute a member")
@app_commands.describe(
    member="Member to unmute"
)
@has_permissions(kick_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    """Unmute a member"""
    try:
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            await interaction.response.send_message(
                f'🔊 {member.mention} has been unmuted.',
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                f'❌ {member.mention} is not muted.',
                ephemeral=False
            )
    except Exception as e:
        await interaction.response.send_message(
            f'❌ Could not unmute {member.mention}. Error: {e}',
            ephemeral=False
        )

# Error handling for missing permissions
@ban.error
@kick.error
@mute.error
@unmute.error
async def mod_commands_error(interaction: discord.Interaction, error):
    if isinstance(error, MissingPermissions):
        if hasattr(interaction, 'response'):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=False)
        else:
            await interaction.channel.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        if hasattr(interaction, 'response'):
            await interaction.response.send_message(f'❌ Missing required argument: {error.param.name}', ephemeral=False)
        else:
            await interaction.channel.send(f'❌ Missing required argument: {error.param.name}')
    else:
        if hasattr(interaction, 'response'):
            await interaction.response.send_message(f'❌ An error occurred: {str(error)}', ephemeral=False)
        else:
            await interaction.channel.send(f'❌ An error occurred: {str(error)}')

@tree.command(name="help", description="Show help for the bot's commands")
async def help_command(interaction: discord.Interaction):
    """Show help for the bot's commands"""
    embed = discord.Embed(
        title="🎉 Giveaway Bot Help",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )
    
    # Giveaway Commands
    embed.add_field(
        name="🎁 Giveaway Commands",
        value="""
        `/giveaway duration:1h winners:1 prize:Example Prize` - Start a new giveaway
        `/reroll message_id:1234567890` - Reroll winners for a giveaway
        
        **Duration Format:**
        - `30m` for 30 minutes
        - `2h` for 2 hours
        - `1d` for 1 day
        - `1w` for 1 week
        """,
        inline=False
    )
    
    # Moderation Commands
    embed.add_field(
        name="🔧 Moderation Commands",
        value="""
        `/mute [@user] 30m [reason]` - Mute a user (or yourself)
        `/unmute @user` - Unmute a user
        `/kick @user [reason]` - Kick a user
        `/ban @user [reason]` - Ban a user
        
        **Examples:**
        - `/mute @User 30m Spamming`
        - `/mute 30m` (mutes yourself)
        - `/kick @User Being rude`
        """,
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=False)

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set")
        exit(1)
    bot.run(token)
