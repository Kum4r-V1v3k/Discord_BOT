from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from typing import *
import sys

class MongoDB():
	
	def __init__(self, host:str="localhost", port:int=27017, serverSelectionTimeout:int=8):
		
		self.client = MongoClient(host, port, serverSelectionTimeoutMS=serverSelectionTimeout)
		self.checkConnection()
		self.db = self.client["db"]
		self.containers = self.db["containers"]
	
	def checkConnection(self) -> None:
		try:
			self.client.admin.command('ping')
		except ConnectionFailure:
			print("SERVER NOT AVAILABLE")
			sys.exit("Exiting....")

	def isUserPresent(self, userid : int) -> bool :
		
		if self.containers.find_one({"_id" : userid}): return True
		else : return False

	def addUser(self, userid : int) -> int:

		if self.isUserPresent(userid): return 53  # 53 = user already exists
		else:
			self.containers.insert_one({"_id":userid, "activeContainers" : [], "isUserBanned" : False})
			return 0 # 0 = success

	def banUser(self, userid : int) -> int:
		
		filters = {"_id" : userid}
		update = {"$set": {'isUserBanned' : True}}
		result = self.containers.update_one(filters, update)

		if result.matched_count == 0 :
			return 33		# 33 = does not exist
		
		elif result.modified_count == 0: 
			return 43 		# 43 = no record updated 
		
		else :
			return 0

	def unbanUser(self, userid : int) -> int:

		filters = {"_id" : userid}
		update = {"$set": {'isUserBanned' : False}}
		result = self.containers.update_one(filters, update)

		if result.matched_count == 0 :
			return 33

		elif result.modified_count == 0: 
			return 43

		else :
			return 0

	def deleteUser(self, userid : int) -> int:
		if not self.containers.find_one({"_id":userid}): return -1 # -1 Failed because no such record exists
		else :
			self.containers.delete_one({"_id":userid})
			return 0


	def isUserBan(self, userid : int) -> Optional[bool]:

		return self.containers.find_one({"_id" : userid})["isUserBanned"]

	def numberOfRunningContainers(self, userid : int) -> int : 

		return len(self.containers.find_one({"_id" : userid})["activeContainers"])

	def addContainer(self, userid : int, containerid : str) -> int: 
		
		if isUserBan(userid) : return 1337  #1337 = User banned
		
		if numberOfRunningContainers(userid) >= 3 : return 127 # 127 = Maxed out usage

		else:
			activeContainers = self.containers.find_one({"_id" : userid})["activeContainers"]
			activeContainers.append(containerid)
			self.containers.update_one({"_id" : userid}, {"activeContainers" : activeContainers})
			return 0

	def removeContainer(self, userid : int, containerid : str) -> int:
		
		activeContainers = self.containers.find_one({"_id": userid})["activeContainers"]

		if containerid not in activeContainers : return 33 # 33 = does not exist
		
		else :
			activeContainers.remove(containerid)
			self.containers.update_one({"_id":userid}, {"activeContainers":activeContainers})
			return 0
			
