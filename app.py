#!/usr/bin/env python3
from time import sleep
from nextcord.ext import commands
from nextcord import File, ButtonStyle, Embed, Interaction, SlashOption, Color, SelectOption, Intents
from nextcord.ui import View, Button, Select
import sys, database, containerdb
from containerdb import MongoDB
from database import Database

containerdb = MongoDB()
database = Database()

GID = [1221327905456656404]
COMMAND_PREFIX = "$"
TOKEN = sys.argv[1]
intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.slash_command(description="Register Yourself!")
async def register_for_thrill(interaction: Interaction):
    
    response = database.create_user(interaction.user.id, interaction.user.name)
    if response == 0:
        embed = Embed(color=0x0080ff, title="SUCCESS", description="You have been added!")
        await interaction.response.send_message(embed=embed)
    
    else:
        response = "User already exists."
        embed = Embed(color=0xe02222, title="ERROR", description=response)
        await interaction.response.send_message(embed=embed)
    
@bot.slash_command(description="Check Your Progress!")
async def check_progress(interaction: Interaction, option : str = SlashOption(description="Select one.", choices={"crypto": "crypto", "web": "web", "rev":"rev", "pwn":"pwn", "gskills":"gskills","forensics":"forensics"})):
    progress_dict = database.get_user_status(interaction.user.id, option)

    if not progress_dict : 
        embed = Embed(color=0xe02222, title="Something went wrong...", description="This was not expected, contact someone from @infobot")
        return await interaction.response.send_message(embed=embed)

    desc = [f"- **{i}** {progress_dict[i]}" for i in progress_dict]
    desc = "\n".join(desc)
    embed = Embed(color=0x5be61c, title=option.title(), description=desc)
    await interaction.response.send_message(embed=embed)

@bot.slash_command(description="Start your challenge!")
async def challenge_start(interaction: Interaction, challengeid : str):
    if len(challengeid) != 6: 
        embed = Embed(color=0xe02222, title="Wrong...", description="Invalid challenge id provided")
        return await interaction.response.send_message(embed=embed)
    
    status = database.startChallenge(interaction.user.id, challengeid)
    if status["started"] :
        embed = Embed(color=0x0080ff, title="Running!", description="Your challenge has started!\n"+status["notes"])
        await interaction.response.send_message(embed=embed)
    else:
        embed = Embed(color=0xe02222, title="Failure!", description="Something went wrong..response from backend:- \n"+status["notes"])
        await interaction.response.send_message(embed=embed)

@bot.slash_command(description="Stop a challenge.")
async def challenge_stop(interaction:Interaction, challengeid : str) :
    if not database.is_chall_started(interaction.user.id, challengeid) :
        embed = Embed(color=0xe02222, title="Error", description="You haven't started this challenge.")
        await interaction.response.send_message(embed=embed)
    check = database.stopChallenge(interaction.user.id, challengeid)
    if check is True:
        embed = Embed(color=0xe02222, title="Done!", description="Your challenge is now stopped.")
        await interaction.response.send_message(embed=embed)

@bot.slash_command(description="Check your Active Challenges!")
async def challenges_active(interaction:Interaction):
    activeChallenges = database.getActiveChallenges(interaction.user.id)
    if activeChallenges : 
        description = "Here you go:- \n"
        description += "\n".join(activeChallenges)
    else:
        description = "No active challenges"
    embed = Embed(color=0xB3D9FF, title="Active Challenges", description=description)
    return await interaction.response.send_message(embed=embed)


@bot.slash_command(description="Challenges List!")
async def challenge_list(interaction:Interaction, category : str = SlashOption(choices={"crypto": "crypto", "web": "web", "rev":"rev", "pwn":"pwn", "gskills":"gskills","forensics":"forensics"})):
    challenge_list = database.get_chall_list(category)

    description = ""
    for difficulty in challenge_list:
        if not challenge_list[difficulty]: continue
        description += f"__**{difficulty.title()}**__\n- " + "\n- ".join([(chall+" "+challenge_list[difficulty][chall]) for chall in challenge_list[difficulty]])

    if not description :
        embed = Embed(color=0xe02222, title="Sorry!", description="No Challenges added in this category")   
    else:
        embed = Embed(color=0xB3D9FF, title="Here you go!", description=description)
    return await interaction.response.send_message(embed=embed)

@bot.slash_command(description="Submit Flag!")
async def submit_flag(interaction : Interaction, challengeid : str, flag : str):
    embed = Embed(color=0xB3D9FF, title="Please Wait", description="Checking challenge status...")
    message = await interaction.response.send_message(embed=embed)
    isChallengeStarted = database.is_chall_started(interaction.user.id, challengeid)
    if not isChallengeStarted : 
        embed = Embed(color=0xe02222, title="Error!", description="Possible Causes:\n1. You did not start the challenge before.\n2. The challenge expired.\nStart the challenge and try again..")
        return await message.edit(embed=embed)
    
    embed = Embed(color=0x9000cc, title="Hmm..", description="Challenge status : Active\nChecking Flag!")
    await message.edit(embed=embed)
    isFlagCorrect = database.check_flag(interaction.user.id, challengeid, flag)
    if isFlagCorrect : 
        embed = Embed(color=0x0080ff, title="Congrats!!", description="Flag is correct!")
        await message.edit(embed=embed)

    else: 
        embed = Embed(color=0xe02222, title="Sorry!", description="Incorrect Flag, please try again!")
        await message.edit(embed=embed)

@bot.command(name="ban_user", description="Ban a fucking user!")
async def ban_user(ctx, userid : int):
    response = database.ban_user(userid)
    if response == 0:
        embed = Embed(color=0xB3D9FF, title="Banned!", description=f"User with uid {userid} is now banned.")
        await ctx.send(embed=embed)
    else:
        embed = Embed(color=0xB3D9FF, title="Error occurred!", description=f"Error occurred, response from db :\n {response}")
        await ctx.send(embed=embed)

@bot.command(name="containers")
async def containers(ctx):
    runningContainersCount = database.getActiveContainersCount()
    if runningContainersCount == 0 :
        await ctx.send(f"Currently no containers are running")
    else:
        await ctx.send(f"Currently **{runningContainersCount}** containers are running.")


@bot.command(name="container")
async def dosomething(ctx, subcommand : str = None, arg : str = None):
    if subcommand == "stop" :
        if not arg : 
            await ctx.send(f"**Usage**\n$container stop <containerid>")
        if arg == "all":
            database.destroyAllContainers()
            await ctx.send("All containers destruction is triggered!")
        else:
            status = database.checkContainerStatus(containerid)
            if status == "running":
                await ctx.send("**Done**\nContainer stopped!")
            else :
                await ctx.send(f"**Error**\nContainer status:- {status}")
    
    elif subcommand == "info":
        if not arg:
            await ctx.send(f"**Usage**\n$container info <containerid>")
        if arg:
            info = database.getContainerInfo(arg)
            if not info:
                await ctx.send(f"No container with id {arg} found")
            else:
                info = [i+" "+info[i]+"\n"for i in info]
                info = "".join(info)
                await ctx.send(f"**Container Info**\n"+info)
    else:
        await ctx.send("**Use $help**")
 
@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}")

if __name__ == "__main__":
    bot.run(TOKEN)
