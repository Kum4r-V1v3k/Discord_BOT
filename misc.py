import docker
import os
import socket
from typing import *
from docker.errors import NotFound

class dock_it():
    def __init__(self) -> None:
        self.client = docker.from_env()
        self.containerDestruction()        

    def botContainersList(self) -> List:
        totalContainers = self.client.containers.list()
        botContainers = []
        for container in totalContainers:
            try: 
                if container.labels["runby"] == "Syre":
                    botContainers.append(container)
            except KeyError :
                continue
        return botContainers 

    def getFreePort(self) -> int:
        s = socket.socket()
        s.bind(('', 0))
        addr = s.getsockname()
        s.close()
        return addr[1]

    def run_container(self, uid : str, chall : Dict):
        freePort = self.getFreePort()
        labels = {"port":str(freePort), "challid":str(chall["_id"]), "uid":str(uid), "runby":"Syre"}
        image = open(os.path.join(chall["path"], "image")).read().strip()
        try:
            container = self.client.containers.run(image, detach=True, labels=labels, ports={80:freePort})
            return container
        except Exception as e:
            print(str(e))
            return None

    def remove_container(self, containerid : str) -> int:
        try:
            container = self.client.containers.get(containerid)
            container.stop()
            container.remove()
            return 0 # Completed with no errors
        except docker.errors.NotFound as e:
            return 1 # Container not found
        except docker.errors.APIError as e:
            return 2 # API Error
        except Exception as e :
            return 3 # Unexpected Error

    def getLabels(self, containerid : str) -> Optional[Dict[str, str]]:
        try:
            labels = self.client.containers.get(containerid).labels
            return labels
        except Exception :
            return None

    def containerDestruction(self):
        allContainers = self.botContainersList()
        for container in allContainers:
            container.stop()
            container.remove()    
