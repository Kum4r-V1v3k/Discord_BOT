from typing import Dict, List, Any, Optional
import pymongo
from containerdb import MongoDB

containerdb = MongoDB()
categories = ["crypto","forensics","rev","pwn","osint","gskills"]

class Database:
    def __init__(self) -> None:
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["db"]
        self.challs = db['challs']
        self.users = db['users']
        self.containers = db['containers']

    def user_exists(self, uid: int) -> int:
        return self.users.count_documents({"_id":uid}, limit = 1)

    def create_user(self, uid: int, name: str) -> int:
        if self.user_exists(uid): return -1
        containerdb.addUser(uid)

        user : Dict[str, Any] = {"_id": uid, "name" : name, "active_challs" : []}

        for category in categories:
            user[category] = []
        self.users.insert_one(user)
        return 0

    def delete_user(self, uid: int) -> int:
        if not self.user_exists(uid) : return -1

        self.users.delete_one({"_id": uid})
        containerdb.deleteUser(uid)

        return 0

    def getActiveChallenges(self, uid:int) -> Optional[Dict]:
        return None if len(self.users.find_one({"_id":uid})["active_challs"]) else self.users.find_one({"_id":uid})["active_challs"]
        
    def get_user_status(self, uid: int, category: str) -> Dict[str,str]:
        completed = self.users.find_one({"_id": uid})[category]
        status = {}
        for chall in self.challs.find({"category":category}, {"_id":0, "name":1}):
            if chall["name"] in completed:
                status[chall["name"]] = "completed"
            else:
                status[chall["name"]] = "not completed"
        return None if not status else status

    def get_chall_list(self, category: str) -> Optional[Dict[str,List[str]]]:
        challs = {"easy":[],"medium":[],"hard":[]}
        if len(list(self.challs.find({"category":category}, {"difficulty":1,"name":1, "_id":1}))) != 0:
            for chall in self.challs.find({"category":category}, {"difficulty":1,"name":1, "_id":1}):
                new_dict = {}
                new_dict[str(chall["_id"])] = chall["name"]
            challs[chall["difficulty"]] = new_dict
        return challs

    def check_flag(self, challid: int, flag : str) -> bool:
        return (self.challs.find_one({"_id":challid}["flag"]) == flag)

    def is_chall_started(self, uid: int, challid : int) -> bool:
        return challid in self.users.find_one({"_id":uid})["active_challs"]

