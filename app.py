#!/usr/bin/env python3
from time import sleep
from nextcord.ext import commands
from nextcord import File, ButtonStyle, Embed, Interaction, SlashOption, Color, SelectOption, Intents
from nextcord.ui import View, Button, Select
import json,sys, os

GID = [1221327905456656404]

TOKEN = sys.argv[1]
intents = Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents)

@bot.slash_command(guild_ids=GID, description="Register Yourself!")
async def register_for_thrill(interaction: Interaction):
    response = database.add_user(str(interaction.user.id), str(interaction.user))
    if response == "SUCCESS":
        embed = Embed(color=0x0080ff, title="SUCCESS", description="You have been added!")
        await interaction.response.send_message(embed=embed)
    else:
        embed = Embed(color=0xe02222, title="ERROR", description=response)
        await interaction.response.send_message(embed=embed)
    
@bot.slash_command(guild_ids=GID, description="Check Your Progress!")
async def check_progress(interaction: Interaction, option : str = SlashOption(description="Select one.", choices={"crypto": "crypto", "web": "web", "rev":"rev", "pwn":"pwn", "gskills":"gskills","forensics":"forensics"}, required=False)):
    progress_dict = database.check_progress(interaction.user.id, option)

    if not progress_dict : 
        embed = Embed(color=0xe02222, title="Something went wrong...", description="This was not expected, contact someone from @infobot")
        return await interaction.response.send_message(embed=embed)

    desc = [f"- **{i}** {progress_dict[i]}" for i in progress_dict]
    desc = "\n".join(desc)
    embed = Embed(color=0x5be61c, title=option, description=desc)
    await interaction.response.send_message(embed=embed)

@bot.slash_command(guild_ids=GID, description="Start your challenge!")
async def challenge_start(interaction: Interaction, challengeid : str):
    if len(challengeid) != 6: 
        embed = Embed(color=0xe02222, title="Wrong...", description="Invalid challenge id provided")
        return await interaction.response.send_message(embed=embed)
    
    status = database.start_challenge(interaction.user.id, challengeid)
    if status :
        embed = Embed(color=0x0080ff, title="SUCCESS", description="Your challenge has started!\n"+status["notes"])
        await interaction.response.send_message(embed=embed)
    else:
        embed = Embed(color=0xe02222, title="Failure", description="Something went wrong, please try again later...")
        await interaction.response.send_message(embed=embed)

@bot.slash_command(guild_ids=GID, description="Submit Flag!")
async def submit_flag(interaction : Interaction, challengeid : str, flag : str):
    embed = Embed(color=0xB3D9FF, title="Please Wait", description="Checking challenge status...")
    message = await interaction.response.send_message(embed=embed)
    isChallengeStarted = database.isChallengeStarted(interaction.user.id, challengeID)
    if not isChallengeStarted : 
        embed = Embed(color=0xe02222, title="Error!", description="Possible Causes:\n1. You did not start the challenge before.\n2. The challenge expired.\nStart the challenge and try again..")
        return await message.edit(embed=embed)
    
    embed = Embed(color=0x9000cc, title="Hmm..", description="Challenge status : Active\nChecking Flag!")
    await message.edit(embed=embed)
    isFlagCorrect = database.check_flag(interaction.user.id, flag)
    if isFlagCorrect : 
        embed = Embed(color=0x0080ff, title="Congrats!!", description="Flag is correct!")
        await message.edit(embed=embed)
    else: 
        embed = Embed(color=0xe02222, title="Sorry!", description="Incorrect Flag, please try again!")
        await message.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}")

if __name__ == "__main__":
    bot.run(TOKEN)
