from typing import Dict, List, Any, Optional
import pymongo
import os
from misc import dock_it

docker = dock_it()
categories = ["crypto","forensics","rev","pwn","osint","gskills","web"]


class Database:
    def __init__(self) -> None:
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["db"]
        self.challs = db['challs']
        self.users = db['users']
        self.containers = db['containers']
        self.container = None

    def user_info(self, username:str) :
        return self.users.find_one({"name":username})

    def user_exists(self, uid: int) -> int:
        return self.users.count_documents({"_id":uid}, limit = 1)

    def create_user(self, uid: int, name: str) -> int:
        if self.user_exists(uid): return -1
        user : Dict[str, Any] = {"_id": uid, "name" : name, "active_challs" : []}
        for category in categories:
            user[category] = []
        user["active_containers"] = dict()
        user["isUserBanned"] = False
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
        return None if len(self.users.find_one({"_id":uid})["active_challs"]) == 0 else self.users.find_one({"_id":uid})["active_challs"]
    
    def banUser(self, username : str) :
        info = self.user_info(username)
        if info is None : return f"No such user found"
        if info["isUserBanned"] : return f"User is already banned"
        else : 
            self.users.update_one({"name":username}, {"$set":{"isUserBanned":True}})
            return f"User is banned"

    def unbanUser(self, username:str):
        info = self.user_info(username)
        if info is None : return f"No such user found"
        if not info["isUserBanned"] : return f"User is not banned"
        else : 
            self.users.update_one({"name":username}, {"$set":{"isUserBanned":False}})
            return f"User is no longer banned"

    def get_user_status(self, uid: int, category: str) -> Dict[str,str]:
        completed = self.users.find_one({"_id": uid})[category]
        status = {}
        for chall in self.challs.find({"category":category}, {"_id":0, "name":1}):
            if chall["name"] in completed:
                status[chall["name"]] = "completed"
            else:
                status[chall["name"]] = "not completed"
        return None if not status else status

    def get_chall_list(self, category: str) -> Dict[str, Dict[str, str]]:
        challs = {"easy":[],"medium":[],"hard":[]}
        if len(list(self.challs.find({"category":category}, {"difficulty":1,"name":1, "_id":1}))) != 0:
            for chall in self.challs.find({"category":category}, {"difficulty":1,"name":1, "_id":1}):
                new_dict = {}
                new_dict[str(chall["_id"])] = chall["name"]
            challs[chall["difficulty"]] = new_dict
        return challs

    def check_flag(self, uid : int, challid: int, flag : str) -> bool:
        if (self.challs.find_one({"_id":challid})["flag"] == flag) :
            self.stopChallenge(uid, challid)
            self.updateStatus(uid, challid)
            return True
        else : return False

    def updateStatus(self, uid : int, challid : int) -> None:
        challengeDetails = self.challs.find_one({"_id" : challid})
        challengeName = challengeDetails["name"]
        challengeCategory = challengeDetails["category"]
        challengeCompleted = self.users.find_one({"_id" : uid})[challengeCategory]
        if challengeName not in challengeCompleted : challengeCompleted.append(challengeName) 
        self.users.update_one({"_id" : uid}, {"$set" : {challengeCategory : challengeCompleted}})
        

    def is_chall_started(self, uid: int, challid : int) -> bool:
        return challid in self.users.find_one({"_id":uid})["active_challs"]

    def isChallengePresent(self, challid : int) -> bool:
        if self.challs.find_one({"_id":challid}) : return True
        else : return False

    def startChallenge(self, uid : int, challid : int) -> Dict[str, Optional[str]] :
        
        if not self.user_exists(uid) : 
            started = False 
            notes = "User not registered!"
            return {"started":started, "notes":notes}
        
        activeChallenges = self.users.find_one({"_id" : uid})["active_challs"]

        if challid in activeChallenges : 
            started = False
            notes = "Challenge already running!"
            return {"started":started, "notes":notes}

        if len(activeChallenges) >=3 : 
            started = False
            notes = "Maximum number of active challenges reached."
            return {"started":started, "notes":notes}

        if not self.isChallengePresent(challid):
            started = False
            notes = "Invalid Challenge ID!"

        else:
            chall = self.challs.find_one({"_id" : challid})
            if chall["category"] == "web":
                code = self.startContainer(chall, uid)
                if code != 0 : 
                    started = False
                    notes = "Backend Error!"
                else:
                    started = True
                    notes = open(os.path.join(chall["path"], "description.txt")).read()
                    notes += "\nhttp://ruleoverworld.duckdns.org:"+self.container.labels["port"]
                    activeChallenges.append(challid)
                    self.users.update_one({"_id":uid}, {"$set": {"active_challs":activeChallenges}})
            else:
                started = True
                notes = open(os.path.join(chall["path"], "description.txt")).read()
                activeChallenges.append(challid)
                self.users.update_one({"_id":uid}, {"$set": {"active_challs":activeChallenges}})
            
        return {"started":started, "notes":notes}
    
    def startContainer(self, chall : Dict, uid : int) -> int:
        self.container = docker.run_container(uid, chall)
        if self.container is None : 
            return -1
        activeContainers = self.users.find_one({"_id":uid})["active_containers"]
        activeContainers[str(chall["_id"])] = str(self.container.id)
        self.users.update_one({"_id":uid},{"$set":{"active_containers":activeContainers}})
        return 0


    def stopChallenge(self, uid : int, challid : str) -> bool:
        chall = self.challs.find_one({"_id":challid})
        if chall["category"] == "web" : 
            docker.remove_container(self.users.find_one({"_id":uid})["active_containers"][challid])
            activeContainers = self.users.find_one({"_id":uid})["active_containers"]
            del activeContainers[challid]
            self.users.update_one({"_id":uid},{"$set":{"active_containers":activeContainers}})
        
        activeChallenges = self.users.find_one({"_id" : uid})["active_challs"]
        activeChallenges.remove(challid)
       
        self.users.update_one({"_id":uid}, {"$set": {"active_challs":activeChallenges}})
        return True


