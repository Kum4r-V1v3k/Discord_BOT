#!/usr/bin/python3
from nextcord.ext import commands
from nextcord import File, ButtonStyle, Embed, Interaction, SlashOption, Color, SelectOption, Intents, TextInputStyle
from nextcord.ui import View, Button, Select, TextInput
import nextcord, os
from database import Database
from misc import dock_it
from dotenv import load_dotenv

load_dotenv()
database = Database()
docker = dock_it()

GID = [1221327905456656404]
COMMAND_PREFIX = "$"
TOKEN = os.getenv("TOKEN")
intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
BAN_EMBED = Embed(color=0xe22222, title="Sorry!", description="You are banned!")
BANNED_USERS = database.bannedUsers()
EPHEMERAL = False
ROLES = {'crypto':['Decryptor', 'Unobfuscator', 'KnowsNothingButCrypto']}
CONTAINERS_LIMIT = 30 
USER_CONTAINER_LIMIT = 3

def toggleEphemeralMessage() -> None:
    global EPHEMERAL 
    EPHEMERAL = not EPHEMERAL
    
def updateBannedUsers() -> None: 
    global BANNED_USERS
    BANNED_USERS = database.bannedUsers()

def getRole(category, index) -> str:
    return ROLES[category][index]

async def assignRole(uid : str, role : str) -> None:
    guild = bot.get_guild(GID[0])
    user = guild.get_member(int(uid))
    roles = guild.roles
    for i in roles:
        if role == i.name : break
    await user.add_roles(i)

async def removeRole(uid, role):
    guild = bot.get_guild(GID[0])
    user = guild.get_member(int(uid))
    roles = guild.roles
    for i in roles:
        if role == i.name : break
    if i in user.roles():
        await user.remove_roles(i)

async def checkCompletionAssignRole(uid, category):
    allChalls = database.allChalls(category)
    totalPoints = 0
    for chall in allChalls:
        if chall["difficulty"] == "easy": totalPoints += 1
        elif chall["difficulty"] == "medium" : totalPoints += 2
        else : totalPoints += 3
    userChalls = database.userChalls(uid,category)
    userPoints = 0
    for chall in userChalls:
        challDiff = database.getDifficulty(chall, category)
        if challDiff == "easy" : userPoints += 1
        elif challDiff == "medium" : userPoints += 2
        else : userPoints += 3
    
    completion = int((userPoints / totalPoints) * 100)
    newRole = None
    previousRole = None
    if completion >= 20 and completion <= 50 :
        newRole = getRole(category, 0)
    elif completion > 50 and completion <= 80:
        newRole = getRole(category, 1)
        previousRole = getRole(category, 0)
    elif completion > 80 :
        newRole = getRole(category, 2)
        previousRole = getRole(category, 1)
    
    if newRole : await assignRole(uid, newRole)
    if previousRole : await removeRole(uid, previousRole)

@bot.slash_command(description="Register Yourself!")
async def register_for_thrill(interaction: Interaction):
    await interaction.response.defer()
    response = database.create_user(interaction.user.id, interaction.user.name)
    if response == 0:
        embed = Embed(color=0x0080ff, title="SUCCESS", description="You have been added!")
        await interaction.followup.send(embed=embed)
    
    else:
        response = "User already exists."
        embed = Embed(color=0xe02222, title="ERROR", description=response)
        await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)
    
@bot.slash_command(description="Check Your Progress!")
async def check_progress(interaction: Interaction, option : str = SlashOption(description="Select one.", choices={"crypto": "crypto", "web": "web", "rev":"rev", "pwn":"pwn", "gskills":"gskills","forensics":"forensics"})):
    if interaction.user.id in BANNED_USERS : 
        return await interaction.response.send_message(embed=BAN_EMBED)

    await interaction.response.defer(ephemeral=EPHEMERAL)
    progress_dict = database.get_user_status(interaction.user.id, option)

    if not progress_dict : 
        embed = Embed(color=0xe02222, title="Something went wrong...", description="This was not expected, contact someone from @infobot")
        return await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)

    desc = [f"- **{i}** {progress_dict[i]}" for i in progress_dict]
    desc = "\n".join(desc)
    embed = Embed(color=0x5be61c, title=option.title(), description=desc)
    await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)

@bot.slash_command(description="Start your challenge!")
async def challenge_start(interaction: Interaction, challengeid : str):
    if interaction.user.id in BANNED_USERS : 
        return await interaction.response.send_message(embed=BAN_EMBED)

    await interaction.response.defer(ephemeral=EPHEMERAL)
    if len(challengeid) != 6: 
        embed = Embed(color=0xe02222, title="Wrong...", description="Invalid challenge id provided")
        return await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)
    
    if database.getCategory(challengeid) in ["pwn", "web"] and CONTAINERS_LIMIT and len(docker.botContainersList()) >= CONTAINERS_LIMIT :
        embed = Embed(color=0xe02222, title="Sorry!", description="Maximum number of containers are running, please wait for your turn.")
        return await interaction.followup.send(embed=embed)

    if database.getCategory(challengeid) in ["pwn", "web"] and USER_CONTAINER_LIMIT and len(database.getUserContainers(interaction.user.name)[0]["active_containers"]) >= USER_CONTAINER_LIMIT:
        embed = Embed(color=0xe02222, title="Sorry!", description=f"You have reached the limit of active containers, please stop one to start one.")
        return await interaction.followup.send(embed=embed)

    status = database.startChallenge(interaction.user.id, challengeid)
    
    if status["started"] :
        embed = Embed(color=0x0080ff, title="Running!", description="Your challenge has started!:white_check_mark:\n"+status["notes"])
        embed.set_footer(text=status["footer"].strip())
        await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL,files=[File(file) for file in status["files"]])
    else:
        embed = Embed(color=0xe02222, title="Failure!", description="Response from backend:- \n"+status["notes"])
        await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)

@bot.slash_command(description="Stop a challenge.")
async def challenge_stop(interaction:Interaction, challengeid : str) :
    if interaction.user.id in BANNED_USERS : 
        return await interaction.response.send_message(embed=BAN_EMBED, ephemeral=EPHEMERAL)
    await interaction.response.defer(ephemeral=EPHEMERAL)

    if not database.is_chall_started(interaction.user.id, challengeid) :
        embed = Embed(color=0xe02222, title="Error", description="You haven't started this challenge.")
        await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)
    check = database.stopChallenge(interaction.user.id, challengeid)
    if check is True:
        embed = Embed(color=0xe02222, title="Done!", description="Your challenge is now stopped.")
        await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)

@bot.slash_command(description="Check your Active Challenges!")
async def challenges_active(interaction:Interaction):
    if interaction.user.id in BANNED_USERS : 
        return await interaction.response.send_message(embed=BAN_EMBED)

    await interaction.response.defer(ephemeral=EPHEMERAL)
    activeChallenges = database.getActiveChallenges(interaction.user.id)
    if activeChallenges : 
        desc = "Here you go:- \n"
        desc += "\n".join(activeChallenges)
    else:
        desc = "No active challenges"
    embed = Embed(color=0xB3D9FF, title="Active Challenges", description=desc)
    return await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)


@bot.slash_command(description="Challenges List!")
async def challenge_list(interaction:Interaction, category : str = SlashOption(choices={"crypto": "crypto", "web": "web", "rev":"rev", "pwn":"pwn", "gskills":"gskills","forensics":"forensics"})):
    if interaction.user.id in BANNED_USERS : 
        return await interaction.response.send_message(embed=BAN_EMBED)

    challenge_list = database.get_chall_list(category)
    desc = ""
    
    for difficulty in challenge_list:
        temp = []
        if  len(challenge_list[difficulty]) == 0: continue
        for challenge in challenge_list[difficulty]:
            temp.append(tuple(challenge.keys())[0] +"    "+tuple(challenge.values())[0])
        desc += "\n\n"
        desc += f"__**{difficulty.title()}**__\n- " + "\n- ".join(temp) 

    if not desc :
        embed = Embed(color=0xe02222, title="Sorry!", description="No Challenges added in this category")   
    else:
        embed = Embed(color=0xB3D9FF, title="Here you go!", description=desc)
    return await interaction.response.send_message(embed=embed, ephemeral=EPHEMERAL)

@bot.slash_command(description="Submit Flag!")
async def submit_flag(interaction : Interaction, challengeid : str, flag : str):
    if interaction.user.id in BANNED_USERS : 
        return await interaction.response.send_message(embed=BAN_EMBED)

    embed = Embed(color=0xB3D9FF, title="Please Wait", description="Checking challenge status...")
    message = await interaction.response.send_message(embed=embed, ephemeral=EPHEMERAL)
    
    isChallengeStarted = database.is_chall_started(interaction.user.id, challengeid)
    if not database.isChallengePresent(challengeid) :
        embed = Embed(color=0xe02222, title="Error!", description="Invalid challenge id entered.")
        return await message.edit(embed=embed)
    if not isChallengeStarted : 
        embed = Embed(color=0xe02222, title="Error!", description="Possible Causes:\n1. You did not start the challenge before.\n2. The challenge expired.\nStart the challenge and try again..")
        return await message.edit(embed=embed)
    
    embed = Embed(color=0x9000cc, title="Hmm..", description="Challenge status : Active\nChecking Flag!")
    await message.edit(embed=embed)
    isFlagCorrect = database.check_flag(interaction.user.id, challengeid, flag)
    if isFlagCorrect : 
        embed = Embed(color=0x0080ff, title="Congrats!!", description="Flag is correct!")
        await message.edit(embed=embed)
        await checkCompletionAssignRole(interaction.user.id , database.getCategory(challengeid))
    else: 
        embed = Embed(color=0xe02222, title="Sorry!", description="Incorrect Flag, please try again!")
        await message.edit(embed=embed)

@bot.command(name="flag")
async def flag(ctx, challengeid:int):
    if "Bot Maker" not in [role.name for role in ctx.author.roles]: return
    
    flag = database.getFlag(challengeid)
    if flag is None: return "Invalid challenge id."
    return await ctx.send("```"+flag+"```")


@bot.group(name="set", invoke_without_command=True)
async def _set(ctx):

    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return

    if ctx.invoked_subcommand is None:
        await ctx.send("**Use $help toggle**")

@_set.command(name="ephemeral")
async def ephemeral(ctx, action : str = None):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    if action is None:
        toggleEphemeralMessage()
        reply = "Ephemeral messages are now on" if EPHEMERAL else "Ephemeral messages are now off"
    else:
        if action.lower() == "on":
            if EPHEMERAL :
                reply = "Ephemeral messages are already on!"
            else: 
                toggleEphemeralMessage()
                reply = "Ephemeral messages are now on!"
        elif action.lower() == "off":
            if not EPHEMERAL:
                reply = "Ephemeral messages are already off!"
            else:
                toggleEphemeralMessage()
                reply = "Ephemeral messages are now off!"

        else:
            reply = "Invalid argument."

    await ctx.send(reply)
   
@bot.group(name="user", invoke_without_command=True)
async def user(ctx):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    if ctx.invoked_subcommand is None:
        await ctx.send(f"User $help user")

@user.command(name="progress")
async def progress(ctx, username : str = None):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    if not username: return await ctx.send("**Usage**\n$user progress username")

    user_info = database.user_info(username)
    if not user_info: return await ctx.send("No such user found!")

    desc = str()
    for category in ["crypto", "rev", "web", "forensics", "osint", "pwn"]:
        if len(user_info[category]) != 0:
            desc += f"**Challs completed in {category}**\n- " + "\n- ".join(user_info[category])+"\n"
    if len(desc) == 0 : desc = "No progress yet."
    await ctx.send(desc)


@user.command(name="status")
async def status(ctx, username : str):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    response = database.isUserBanned(username)
    if response is None : reply = "No such user found"
    if response : reply = "User is banned"
    else : reply = "User is not banned"
    await ctx.send(reply)

@user.command(name="ban")
async def ban(ctx, username:str):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    response = database.banUser(username)
    updateBannedUsers()
    await ctx.send(response)

@user.command(name="unban")
async def unban(ctx, username:str):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    response = database.unbanUser(username)
    updateBannedUsers()
    await ctx.send(response)

@user.command(name="remove")
async def remove(ctx, username:str):
    if "Bot Maker" not in [role.name for role in ctx.author.roles]: return
    user = database.user_info(username)
    response = database.delete_user(user["_id"])
    if response == 0:
        await ctx.send("User deleted.")
    else : 
        await ctx.send("No such user has registered.")


@bot.group(name="containers",description="Manage Containers!", invoke_without_command=True)
async def containers(ctx):

    if "Bot Maker" not in [role.name for role in ctx.author.roles] : return
    if ctx.invoked_subcommand is None:
        await ctx.send("Use $help containers")

@containers.command(name="count")
async def count(ctx):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    runningContainers = len(docker.botContainersList())
    if runningContainers == 0 : await ctx.send("No containers running.")
    elif runningContainers == 1: await ctx.send("1 container in running")
    else : await ctx.send(f"{runningContainers} container are running.") 

@containers.command(name="list")
async def list(ctx, username:str=None):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    getContainers = database.getUserContainers(username)
    response = ""
    for i in getContainers:
        if len(i["active_containers"]) != 0 :
            response += f"Containers running for User:- **{i["name"]}**\n" + "\n".join(i["active_containers"].values())
    if not response == 0: response = "No containers active"
    await ctx.send(response)

@containers.command(name="remove")
async def remove(ctx, id : str = None):
    if "Bot Maker" not in [ role.name for role in ctx.author.roles]: return
    if not id : 
        return await ctx.send("**Usage**\n$containers remove all/containerid")
    allContainers = docker.botContainersList()
    
    if len(allContainers) == 0:
        return await ctx.send("Nothing to remove.")

    if id == "all":
        await ctx.send("All containers destruction is triggered!")
        for container in allContainers:
            labels = container.labels
            database.stopChallenge(labels["uid"], labels["challid"])
    else:
        containerids = [i.id for i in allContainers]
        if id not in containerids:
            await ctx.send("No container with given id is running.")
        else:
            for container in allContainers : 
                if container.id == id : break
            labels = container.labels
            database.stopChallenge(labels["uid"], labels["challid"])
            await ctx.send("Container stopped!")

@bot.event
async def on_ready():
    await bot.sync_all_application_commands()
    print(f"Logged in as: {bot.user.name}")

if __name__ == "__main__" : 
    bot.run(TOKEN)
