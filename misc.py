import docker
import os
import socket
from typing import *

class dock_it():
    def __init__(self):
        self.client = docker.from_env()

    def getFreePort(self) -> int:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        addr = s.getsockname()
        s.close()
        return addr[1]

    def run_container(self, uid : str, chall : Dict):
        freePort = self.getFreePort()
        labels = {"port":str(freePort), "challid":str(chall["_id"]), "uid":str(uid)}
        image = open(os.path.join(chall["path"], "project/image")).read().strip()
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

    def getLabels(self, containerid : str) -> Dict[str, str]:
        try:
            labels = client.containers.get(containerid).labels
            return labels
        except Exception :
            return None





        
