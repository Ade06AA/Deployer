"""
user object model
"""
from os import getenv
from fabric import Connection
from requests import delete

from models.base import Base
import models
from deployer.main import Deployer

class Build(Base):
    name = "build"
    def __init__(self, project_id, _type: str, _repo=None, _id=None,
                 userName=None, userPass=None, Nid=None, rootPass=None, dbName=None,
                 projectPort=None, relativeProjectId=None, network=None,
                 runCommand=None, buildCommand=None, envs=None,
                 installCommand=None, webServer=None, projectDir=None):
        """
        to add build finis time
        """
        # id is curently useless
        self.keys = ["id", "build_num",
                     "created_at", "project_id",
                    "repo", "building", "status", "runCommand",
                    "envs", "buildCommand", "installCommand", "projectDir",
                     "webServer"]
        super().__init__()
        if _id:
            self.id = _id
        self.project_id = project_id
        self.repo = _repo
        _type = _type.lower()
        kwargs = {}
        if _type in ["flask", "react", "next", "django"]:
            kwargs = {
                "repoUrl": _repo, "runCommand": runCommand, "envs": envs,
                "buildCommand": buildCommand, "installCommand": installCommand,
                "projectDir": projectDir, "webServer": webServer
            }
            for i, j in kwargs.items():
                setattr(self, i, j)
        elif _type == "mongodb":
            kwargs = {"userName": userName,"project_id": relativeProjectId,
                     "userPass": userPass}
        elif _type == "mysql":
            kwargs = {"userName": userName, "userPass": userPass,
                     "project_id": relativeProjectId, "rootPass": rootPass}
        self.job = Deployer(id=self.id, Nid=Nid,
                            projectType=_type, projectPort=projectPort, network=network, **kwargs)
        self.build_num = self.job.buildNum

    @classmethod
    def Delete(cls, id):
        """
        delete all builds on project with <id:project_id>
        """
        # delete deploy
        # delete project from database
        # delete from jenkins
        build_id = Build.find({"project_id": id}, {"id": 1})
        if len(build_id) > 0:

            build_id = build_id[0]["id"]
            Build.delete({'id': build_id})
            cls.deletedeploy(build_id, True)

        return

    @classmethod
    def deletedeploy(cls, id, network=False):
        # delete container and also build data in jenkins
        # but if it is suspend only delete the the container
        command1 = f"sudo docker rm -f {id}-name"
        command2 = f"sudo docker rm -f {id}-network"
        host = getenv("HOST_IP")
        user = "ubuntu"
        certificate = getenv("SSH_CERT")
        res = Connection(host=host, user=user,
                         connect_kwargs={"key_filename": certificate})
        dd= res.run(command1)
        if network:
            dd= res.run(command2)

        return

    @classmethod
    def prebuild(cls, Id):
        # use fabric to create network
        command = f"sudo docker network create {Id}-network"
        host = getenv("HOST_IP")
        user = "ubuntu"
        certificate = getenv("SSH_CERT")
        res = Connection(host=host, user=user,
                         connect_kwargs={"key_filename": certificate})
        res.run(command)
        print("@running")
        # raise error in case of fail

        return True

    def build(self, port):
        """
        build
        """
        try:
            self.job.build(port=port)
        except Exception as e:
            models.handleError(e)
            return False
        self.building = True
        self.status = None
        return True

    def rebuild(self, port=None):
        """
        rebuild
        """
        try:
            self.__class__.deletedeploy(self.id)
            self.job.build(port, self.id)
        except Exception as e:
            models.handleError(e)
            return False
        self.building = True
        self.status = None
        return True

    @classmethod
    def buildOutput(cls, id, num=None):
        """
        """
        job = Deployer(id=id)
        output = None
        try:
            output = job.getOutput(build_num=num)
        except Exception as e:
            raise e
        return output

    @classmethod
    def status(cls, id, num=None):
        """
        """
        job = Deployer(id=id)
        status = (None, None)
        try:
            print("status")
            status = job.getStatus(build_num=num)
            print(status)
        except Exception as e:
            raise e
        return status

    @classmethod
    def updateBuildStat(cls, obj, caller=None):
        """
        update database
        """
        stats= cls.status(obj["id"], obj["build_num"])
        models.storage.update(cls, obj,
                              {
                              "building": False if caller == "jenkins" else stats[0],
                              "status": stats[1]
                              })
