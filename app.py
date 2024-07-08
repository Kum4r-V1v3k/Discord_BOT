import nextcord 
from nextcord.ext import commands
from nextcord import Intents, Interaction, Embed, File
from config import * 
from typing import Dict, List, Optional 
from database import Database
from misc import dock_it
from nextcord.ext.commands.errors import MissingAnyRole

runningContainers = dict()
database = Database()
docker = dock_it()


intents = Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)



def updateBannedUsers() -> None:
    global BANNED_USERS
    BANNED_USERS = database.bannedUsers()

def toggleEphemeralMessage() -> None:
    global EPHEMERAL
    EPHEMERAL = not EPHEMERAL

def calcUserScore(userid:str, category:str) -> int :
    userChalls = database.userDetails(uid=userid).get(category)
    score = 0
    for chall in userChalls :
        difficulty = database.getDifficulty(name=chall, category=category)
        if difficulty == "easy": score += 1
        elif difficulty == "medium": score += 2
        else : score += 3
    return score 

async def deleteAllRoles(userid:int) -> None:
    guild = bot.get_guild(GID[0])
    user = guild.get_member(userid)
    roles = user.roles 
    toDelete = []
    for role in roles:
        if role.name in ALL_ROLES:
            toDelete.append(role)
    await user.remove_roles(*toDelete)

async def modifyRole(userid:str, role:str, action:str) -> None :
 
    guild = bot.get_guild(GID[0])    
    roles = guild.roles 
    allotRole = None 
    for _role in roles:
        if _role.name == role:
            allotRole = _role 
            break 
    if not allotRole:
        return   
    member = guild.get_member(int(userid))
    if action == "assign":
        await member.add_roles(allotRole)
    else :
        await member.remove_roles(allotRole)


async def checkCompletionAssignRole(userid:str, category:str) -> None :
    categoryTotal = database.getTotalScore(category=category)
    userTotal = calcUserScore(userid=userid, category=category)
    completion = (userTotal/categoryTotal)*100
    if completion >= 20 and completion < 50:
        await modifyRole(userid, ROLES[category][0], action="assign")
    elif completion >= 50 and completion < 80:
        await modifyRole(userid, ROLES[category][1], action="assign")
        await modifyRole(userid, ROLES[category][0], action="remove")
    else:
        await modifyRole(userid, ROLES[category][2], action="assign")
        await modifyRole(userid, ROLES[category][1], action="remove")

async def checkUser(interaction:Interaction) -> bool:
    userid : str = str(interaction.user.id)
    if userid in BANNED_USERS:
        await interaction.followup.send(embed=BAN_EMBED)
        return False
    if database.isUserPresent(int(userid)) != 1:
        await interaction.followup.send(embed=NOT_REGISTERED_EMBED)
        return False
    return True 

@bot.slash_command(name="ping", description="Check Bot Latency.", guild_ids=GID)
async def ping(interaction:Interaction):

    await interaction.response.send_message(f"Pong! In {round(bot.latency*1000)}ms.", ephemeral=EPHEMERAL) 
    # Copied from stackexchange

@bot.slash_command(name="about", description="In case you want to know more about our lonely Syre!", guild_ids=GID)
async def about(interaction:Interaction):

    await interaction.response.send_message(embed=ABOUT_EMBED)

@bot.slash_command(name="register", description="Register yourself to get Started!", guild_ids=GID)    
async def register(interaction:Interaction):
    
    user : nextcord.User = interaction.user
    response : int = database.addUser(name=user.name, uid=user.id) 
    if response == 0:
        await interaction.response.send_message(embed=ON_REGISTRATION_SUCCESS_EMBED)
    
    else : 
       await interaction.response.send_message(embed=ON_REGISTRATION_FAILURE_EMBED, ephemeral=EPHEMERAL) 

@bot.slash_command(name="list_challenges", description="Take a look of available challenges.", guild_ids=GID)
async def listChallenges(interaction:Interaction, category:str=CATEGORY_SELECTION): 
    
    await interaction.response.defer(ephemeral=EPHEMERAL)
    
    check : bool = await checkUser(interaction)
    if check is False:
        return 

    challList : str = database.getChallList(category) # challList does not mean that it will be a list lol
    if challList:
        CHALL_DESC_EMBED = challEmbed(desc=challList) # Check challEmbed function in config.py to modify looks
        await interaction.followup.send(embed=CHALL_DESC_EMBED, ephemeral=EPHEMERAL)
    else:
        await interaction.followup.send(embed=NO_CHALL_DESC_EMBED, ephemeral=EPHEMERAL)

@bot.slash_command(name="start_challenge", description="Start your challenge!", guild_ids=GID)
async def startChallenge(interaction:Interaction, challengeid:str):
    
    await interaction.response.defer(ephemeral=EPHEMERAL)

    user : nextcord.User = interaction.user 
    check : bool = await checkUser(interaction)
    if check is False:
        return

    if not database.challExists(challengeid):
        await interaction.followup.send(embed=CHALL_NOT_FOUND_EMBED, ephemeral=EPHEMERAL)
        return 
    
    if database.isChallRunning(uid=user.id, challid=challengeid):
        await interaction.followup.send(embed=CHALL_ALREADY_RUNNING_EMBED, ephemeral=EPHEMERAL)
        return 
    
    if len(database.userDetails(uid=user.id).get("active_challs")) >= MAX_ACTIVE_CHALLENGES :
        await interaction.followup.send(embed=MAX_ACTIVE_CHALLENGES, ephemeral=EPHEMERAL)
        return

    if database.getChallCategory(challengeid) in ["pwn", "rev"]:
        if len(docker.botContainersList()) >= MAX_CONTAINERS_COUNT :
            await interaction.followup.send(embed=MAX_CONTAINERS_ERROR_EMBED, ephemeral=EPHEMERAL)
            return 
    
        if len(database.userDetails(uid=user.id).get("active_containers")) >= MAX_CONTAINERS_COUNT_PER_USER :
            await interaction.followup.send(embed=MAX_CONTAINERS_PER_USER_ERROR_EMBED, ephemeral=EPHEMERAL)
            return 


    response : Dict[str, str | List] = database.startChallenge(uid=user.id, challid=challengeid)
    if response['started'] is False:
        embed : nextcord.Embed = Embed(title="Oops!", description="Error occurred:-\n"+response["notes"])
        await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)
        return 

    embed : nextcord.Embed = Embed(title="Running!", description="Your challenge has started! :white_check_mark:\n"+response["notes"])
    await interaction.followup.send(embed=embed, files=[File(file) for file in response["files"]], ephemeral=EPHEMERAL)

@bot.slash_command(name="stop_challenge", description="Stop a running challenge", guild_ids=GID)
async def stopChallenge(interaction : Interaction, challengeid:str):

    await interaction.response.defer()

    user : nextcord.User = interaction.user 
    check : bool = await checkUser(interaction)
    if check is False:
        return 
    
    if not database.isChallRunning(uid=user.id, challid=challengeid):
        await interaction.followup.send(embed=CHALL_NOT_STARTED_EMBED, ephemeral=EPHEMERAL)
        return 
    
    if database.getChallCategory(challengeid) in ["pwn", "web"]:
        for i in runningContainers:
            if challengeid in runningContainers[i] and user.id in runningContainers[i]:
                break
        try:
            del runningContainers[i]
        except Exception as e : 
            print(str(e))
 
    challStop : bool = database.stopChallenge(uid=user.id, challid=challengeid)
    if challStop : 
        await interaction.followup.send(embed=CHALL_STOPPED_EMBED, ephemeral=EPHEMERAL)

@bot.slash_command(name="active_challenges", description="Check your running challenges.", guild_ids=GID)
async def activeChallenges(interaction:Interaction):
    
    await interaction.response.defer()

    check : bool = await checkUser(interaction)
    if check is False:
        return 

    activeChalls : Optional[List[str]] = database.getActiveChallenges(interaction.user.id)
    embed : nextcord.Embed = Embed(title="Active Challenges", description="\n".join(activeChalls) if activeChalls else "None")
    await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)

@bot.slash_command(name="check_progress", description="Check your progress.", guild_ids=GID)
async def checkProgress(interaction:Interaction, category:str=CATEGORY_SELECTION):

    user : nextcord.User = interaction.user    
    await interaction.response.defer(ephemeral=EPHEMERAL)
    check : bool = await checkUser(interaction)
    if check is False:
        return 

    progress_dict : Dict[str, str] = database.getUserStatus(uid=user.id, category=category)
    if not progress_dict : 
        await interaction.followup.send(embed=NO_PROGRESS_ERROR_EMBED, ephemeral=EPHEMERAL)
        return 

    desc : List = [f"- **{i}** {progress_dict[i]}" for i in progress_dict]
    desc : str = "\n".join(desc)
    embed : nextcord.Embed = Embed(color=0x5be61c, title=category.title(), description=desc)
    await interaction.followup.send(embed=embed, ephemeral=EPHEMERAL)

@bot.slash_command(name="submit_flag", description="I waited an eternity for this.")
async def submit_flag(interaction:Interaction, challengeid:str, flag:str):
 
    await interaction.respond.defer()
    user : nextcord.User = interaction.user 
    check : bool = await checkUser(interaction)
    if check is False:
        return 

    message : nextcord.Message = await interaction.followup.send(embed=CHALL_STATUS_CHECK_EMBED, ephemeral=EPHEMERAL)
    
    if not database.challExists(challid=challengeid):
        await message.edit(embed=CHALL_NOT_FOUND_EMBED)
        return 

    if not database.isChallRunning(challid=challengeid):
        await message.edit(embed=CHALL_NOT_RUNNING_EMBED)
        return 

    message = await message.edit(embed=CHALL_ACTIVE_EMBED)

    if database.checkFlag(uid=user.id, flag=flag):
        await message.edit(embed=CORRECT_FLAG_EMBED)
        await checkCompletionAssignRole(userid=user.id, category=database.getChallCategory(challid=challengeid))
    else: 
        await message.edit(embed=INCORRECT_FLAG_EMBED)

@bot.command(name="flag")
@commands.has_any_role(*ADMIN_ROLES)
async def flag(ctx, challengeid:str):

    flag = database.getFlag(challengeid)
    await ctx.send("```"+flag+"```")

@bot.group(name="set", invoke_without_command=True)
@commands.has_any_role(*ADMIN_ROLES)
async def _set(ctx):
    
    if ctx.invoked_subcommand is None:
        await ctx.send("**Use $help set**")

@_set.command(name="ephemeral")
@commands.has_any_role(*ADMIN_ROLES)
async def ephemeral(ctx, action : str = None):
    
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
 

@bot.group(name="user", invoke_without_subcommand=True)
@commands.has_any_role(*ADMIN_ROLES)
async def user(ctx:commands.context):

    if ctx.invoked_subcommand is None:
        await ctx.send("Use $help user.")

@user.command(name="progress")
@commands.has_any_role(*ADMIN_ROLES)
async def progress(ctx:commands.context, username:str):

    if username is None:
        await ctx.send("Please provide a username.")
        return 
    user_info = database.user_info(username)
    if not user_info: return await ctx.send("No such user found!")

    desc = ""
    for category in CHOICES:
        if len(user_info[category]) != 0:
            desc += f"**Challs completed in {category}**\n- " + "\n- ".join(user_info[category])+"\n"
    if len(desc) == 0 : desc = "No progress yet."
    await ctx.send(desc)

@user.command(name="status")
@commands.has_any_role(*ADMIN_ROLES)
async def status(ctx, username : str):

    if username is None:
        await ctx.send("Please provide a username.")
        return 
    response = database.isUserBanned(username)
    if response is None : reply = "No such user found"
    if response : reply = "User is banned"
    else : reply = "User is not banned"
    await ctx.send(reply)

@user.command(name="ban")
@commands.has_any_role(*ADMIN_ROLES)
async def ban(ctx, username:str):

    if username is None:
        await ctx.send("Please provide a username.")
        return 
    response = database.banUser(username)
    updateBannedUsers()
    await ctx.send(response)

@user.command(name="unban")
@commands.has_any_role(*ADMIN_ROLES)
async def unban(ctx, username:str):

    if username is None:
        await ctx.send("Please provide a username.")
        return 
    response = database.unbanUser(username)
    updateBannedUsers()
    await ctx.send(response)

@user.command(name="remove")
@commands.has_any_role(*ADMIN_ROLES)
async def remove(ctx, username:str):

    
    if username is None:
        await ctx.send("Please provide a username.")
        return 

    user : Dict = database.user_info(username)
    await deleteAllRoles(int(user["_id"]))

    response : int = database.delete_user(user["_id"])

    if response == 0:
        await ctx.send("User deleted.")
    else : 
        await ctx.send("No such user has registered.")


@bot.group(name="containers",description="Manage Containers!", invoke_without_command=True)
@commands.has_any_role(*ADMIN_ROLES)
async def containers(ctx):

    if ctx.invoked_subcommand is None:
        await ctx.send("Use $help containers")

@containers.command(name="count")
@commands.has_any_role(*ADMIN_ROLES)
async def count(ctx):

    runningContainers = len(docker.botContainersList())
    if runningContainers == 0 : await ctx.send("No containers running.")
    elif runningContainers == 1: await ctx.send("1 container in running")
    else : await ctx.send(f"{runningContainers} container are running.") 

@containers.command(name="list")
@commands.has_any_role(*ADMIN_ROLES)
async def list(ctx : commands.Context, username:str=None):

    getContainers : List = database.getUserContainers(username)
    response : str = ""
    for i in getContainers:
        if len(i["active_containers"]) == 0 : continue
        response += f"**Containers running for {i["name"]}**\n"
        for _, containerid in zip(i["active_containers"].keys(), i["active_containers"].values()) :
            labels = docker.getLabels(str(containerid))
            if labels is None : 
                response +=  f"```Container with id:- {containerid} for challengeid:- {_} stopped unexpectedly during runtime.```"
                continue 
            keys, values = labels.keys(), labels.values()
            temp = [key+" : "+value for key,value in zip(keys,values)]    
            response += "```"+"\n".join(temp)+"```"
        

    if not response : response = "No containers active."
    await ctx.send(response)

@containers.command(name="remove")
@commands.has_any_role(*ADMIN_ROLES)
async def remove(ctx, id : str = None):

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
    print(f"{bot.user.name} is ready!")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, MissingAnyRole):
        await ctx.send(embed=RESTRICTED_EMBED)

if __name__ == "__main__":
    bot.run(TOKEN)