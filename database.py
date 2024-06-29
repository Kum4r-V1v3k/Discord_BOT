from typing import Dict, List, Any, Optional
import pymongo
import os
from misc import dock_it


docker = dock_it()
categories = ["crypto","forensics","rev","pwn","osint","gskills","web"]

class Database:
    def __init__(self, resetChallenges=True) -> None:
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["db"]
        self.challs = db['challs']
        self.users = db['users']
        self.containers = db['containers']
        self.container = None
        if resetChallenges:
            self.resetChallenges()
        
    def resetChallenges(self):
        self.users.update_many({}, {"$set": {"active_containers":dict(), "active_challs":list()}})

    def bannedUsers(self):
        return [i["_id"] for i in list(self.users.find({"isUserBanned":True}))]
    
    def user_info(self, username:str) :
        return self.users.find_one({"name":username})

    def user_exists(self, uid: int) -> int:
        return self.users.count_documents({"_id":uid}, limit = 1)

    def create_user(self, uid: int, name: str) -> int:
        if self.user_exists(uid): return -1
        
        user : Dict[str, Any] = {"_id": uid, "name" : name, "active_challs" : [], "active_containers" : {}, "isUserBanned":False}
        for category in categories:
            user[category] = []
        self.users.insert_one(user)
        
        return 0

    def isUserBanned(self, username:str) -> bool:
        info = self.user_info(username)
        return info["isUserBanned"] if info is not None else None

    def delete_user(self, uid: int) -> int:
        if not self.user_exists(uid) : return -1
        
        self.users.delete_one({"_id": uid})

        return 0

    def getActiveChallenges(self, uid:int) -> Optional[Dict]:

        if len(self.users.find_one({"_id":uid})["active_challs"]) == 0 : return None
        
        else: 
            toReturn = list()
            activeChalls = self.users.find_one({"_id":uid})["active_challs"]
            for chall in activeChalls : 
                name = self.challs.find_one({"_id":chall}, {"name":1, "_id":0})
                toReturn.append(chall + "  " + name["name"])
            return toReturn

    def banUser(self, username : str) -> str:
        info = self.user_info(username)
        if info is None : return f"No such user found"
        if info["isUserBanned"] : return f"User is already banned"
        else : 
            self.users.update_one({"name":username}, {"$set":{"isUserBanned":True}})
            return f"User is banned"

    def unbanUser(self, username:str) -> str:
        info = self.user_info(username)
        if info is None : return f"No such user found"
        if not info["isUserBanned"] : return f"User is not banned"
        else : 
            self.users.update_one({"name":username}, {"$set":{"isUserBanned":False}})
            return f"User is no longer banned"

    def allChalls(self,category):
        return self.challs.find({"category":category})
    
    def getDifficulty(self,name,category) -> str:
        return self.challs.find_one({"name":name, "category":category}).get("difficulty")
        
    def userChalls(self,uid,category):
        return self.users.find_one({"_id":uid}).get(category)

    def getCategory(self,challengeid) -> str:
        return self.challs.find_one({"_id":challengeid}).get("category")

    def get_user_status(self, uid: int, category: str) -> Dict[str,str]:
        completed = self.users.find_one({"_id": uid})[category]
        status = {}
        for chall in self.challs.find({"category":category}, {"_id":0, "name":1}):
            if chall["name"] in completed:
                status[chall["name"]] = "Completed"
            else:
                status[chall["name"]] = "Not Completed"
        return None if not status else status

    def get_chall_list(self, category: str) -> Dict[str, Dict[str, str]]:
        challs = {"easy":[],"medium":[],"hard":[]}
        
        for chall in self.challs.find({"category":category}):
                challs[chall["difficulty"]].append({str(chall["_id"]) : chall["name"]})
            
        return challs

    def check_flag(self, uid : int, challid: int, flag : str) -> bool:
        
        if (self.challs.find_one({"_id":challid})["flag"] == flag) :
            self.stopChallenge(uid, challid)
            self.updateStatus(uid, challid)
            return True
        else : return False

    def getFlag(self, challid:int) -> str:
        flag = self.challs.find_one({"_id":str(challid)})
        return flag["flag"] if flag else "Not found"

    def updateStatus(self, uid : int, challid : int) -> None:
        challDetails = self.challs.find_one({"_id" : challid})
        challName = challDetails["name"]
        challCategory = challDetails["category"]
        challCompleted = self.users.find_one({"_id" : uid})[challCategory]
        if challName not in challCompleted : challCompleted.append(challName) 
        self.users.update_one({"_id" : uid}, {"$set" : {challCategory : challCompleted}})
        

    def is_chall_started(self, uid: int, challid : int) -> bool:
        return challid in self.users.find_one({"_id":uid})["active_challs"]

    def isChallengePresent(self, challid : int) -> bool:
        if self.challs.find_one({"_id":challid}) : return True
        else : return False

    def startChallenge(self, uid : int, challid : int) -> Dict :
        
        if not self.user_exists(uid) : 
            started = False 
            notes = "User not registered!"
            return {"started":started, "notes":notes}
        
        activeChallenges = self.users.find_one({"_id" : uid})["active_challs"]

        if challid in activeChallenges : 
            started = False
            notes = "Challenge already running!"
            return {"started":started, "notes":notes}

        if len(activeChallenges) >=8 : 
            started = False
            notes = "Maximum number of active challenges reached."
            return {"started":started, "notes":notes}

        files = []

        if not self.isChallengePresent(challid):
            started = False
            notes = "Invalid Challenge ID!"

        else:
            chall = self.challs.find_one({"_id" : challid})
            footer = None
            if chall["category"] in ["web", "pwn"]:
                code = self.startContainer(chall, uid)
                if code != 0 : 
                    started = False
                    notes = "Backend Error!"
                else:
                    started = True
                    notes = open(os.path.join(chall["path"], "description.txt")).read()
                    if chall["category"] == "web":
                        notes += "\nhttp://bondjames.sytes.net:"+self.container.labels["port"]
                    else:
                        notes.strip()
                        notes += f"\n`nc bondjames.sytes.net {self.container.labels['port']}`"

                    activeChallenges.append(challid)
                    self.users.update_one({"_id":uid}, {"$set": {"active_challs":activeChallenges}})
                    footer = chall["name"]+":"+chall["_id"]
                    filesPath = os.path.join(chall["path"], "files")
                    for file in os.listdir(filesPath)  :
                        files.append(os.path.join(filesPath, file))


            else:
                started = True
                notes = open(os.path.join(chall["path"], "description.txt")).read()
                activeChallenges.append(challid)
                self.users.update_one({"_id":uid}, {"$set": {"active_challs":activeChallenges}})
                footer = "\n\n"+chall["_id"]+"\t"+chall["name"]
                filesPath = os.path.join(chall["path"], "files")
                for file in os.listdir(filesPath) :
                    files.append(os.path.join(filesPath, file))

        
        return {"started":started, "notes":notes, "files":files, "footer":footer}
    
    def startContainer(self, chall : Dict, uid : int) -> int:
        self.container = docker.run_container(uid, chall)
        if self.container is None : 
            return -1
        activeContainers = self.users.find_one({"_id":uid})["active_containers"]
        activeContainers[str(chall["_id"])] = str(self.container.id)
        self.users.update_one({"_id":uid},{"$set":{"active_containers":activeContainers}})
        return 0

    def getUserContainers(self, username:str = None):
        if username:
            return list(self.users.find({"name": username}))
        else: 
            return list(self.users.find())

    
    def stopChallenge(self, uid : int, challid : str) -> bool:
        chall = self.challs.find_one({"_id":challid})
        uid = int(uid)
        if chall["category"] in ["web","pwn"] : 
            docker.remove_container(self.users.find_one({"_id":uid})["active_containers"][challid])
            activeContainers = self.users.find_one({"_id":uid})["active_containers"]
            del activeContainers[challid]
            self.users.update_one({"_id":uid},{"$set":{"active_containers":activeContainers}})
        
        activeChallenges = self.users.find_one({"_id" : uid})["active_challs"]
        try:
            activeChallenges.remove(challid) 
        except Exception as e:
            print(str(e))
       
        self.users.update_one({"_id":uid}, {"$set": {"active_challs":activeChallenges}})
        return True

