#!/usr/bin/env python3
"""
Module that handels the main deployment
"""
from os import getenv
import jenkins
from deployer.myxml import generate_xml
from deployer.util import pythonSetup, nodeSetup, mysqlSetup, mongodbSetup


class Deployer:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id") # remove cration od id #temp
        self.Nid = kwargs.get("Nid") # network id
        if self.Nid is None:
            self.Nid = self.id
        self.server = jenkins.Jenkins(
            url=  getenv("JENKINS_URL","http://localhost:8080"),
            username= getenv("JENKINS_USER", "OadeO6"), # use an env file
            password= getenv("JENKINS_PASSWD", "2a8f52fb4bde48069e2f61049f9b314e")
        )
        self.kwargs = kwargs
        # FLASK_RUN_PORT FLASK_APP
        envs = kwargs.get("envs")
        envs = [] if not envs else envs[1:]
        self.envDict = {} if not envs else {b.split('=')[0]: b.split('=')[1]  for b in envs}
        self.pType = kwargs.get("projectType", "flask")
        self.projectPort = kwargs.get("projectPort")
        self.repo = kwargs.get("repoUrl") # remove cration od id #temp
        self.network = kwargs.get("network")
        self.runCommand = kwargs.get("runCommand")
        self.installCommand = kwargs.get("installCommand")
        self.buildCommand = kwargs.get("buildCommand")
        self.projectDir = kwargs.get("projectDir")
        self.webServer = kwargs.get("webServer")
        print("@network")
        #"https://github.com/Ade06AA/mytest"
        if self.server.job_exists(f"{self.id}-job"):
            self.buildNum = self.server.get_job_info(f'{self.id}-job')['nextBuildNumber']
        else:
            self.buildNum = 1
        api_addr = getenv("API_ADDR")
        api_port = getenv("API_PORT")
        self.api2Endpoint = f'http://{api_addr}:{api_port}/user/project/{self.id}/{self.buildNum}/api2'

    def getStatus(self, job_name=None, build_num=None):
        """
        get the status of a build
        returns a tuple that contain:
            building : if the jub is still in building process
            result: the build result
        """
        if job_name is None:
            job_name = f'{self.id}-job'
        if build_num is None:
            build_num = self.buildNum
        status = (None, None)
        try:
            status = self.server.get_build_info(job_name, build_num)
            status = status["building"], status["result"]
        except jenkins.JenkinsException as e:
            pass
        return status

    def getOutput(self, job_name=None, build_num=None):
        """
        get the output of the exicution
        """
        if job_name is None:
            job_name = f'{self.id}-job'
        if build_num is None:
            build_num = self.buildNum
        output = None
        try:
            output = self.server.get_build_console_output(
                job_name, build_num)
        except jenkins.JenkinsException as e:
            pass
        return output

    def getDEnv(self, envDict):
        """
        format the env to be suitable for docker
        """
        env = ""
        for i in envDict:
            emv += " -e {}={} ".format(i, envDict[i])
        return env

    def generate_xml_config(self, host_port):
        code = []
        projectPort = self.envDict.get("FLASK_RUN_PORT", "5000")
        if self.network == 'create2':
            network = f"sudo docker network  create {self.Nid}-network"
        else:
            network = "echo 'do docker network check'"
        Setup = ["set up ",
                 network,
                "scriptNext", # the script shoud be removed because this file is not meant to understand hoe to interact with jenkins
                 f"""
                 script {{
                    def theRepo = sh(script: "ls -d theRepo-* | head -n 1", returnStdout: true).trim()
                    if (theRepo){{
                            sh "cp -r ${{theRepo}} theRepo-${{currentBuild.number}}; echo '+ @show1@ copying available repository'"
                            sh "cd theRepo-${{currentBuild.number}}; git pull ; echo '+ @show1@ updating copied repository'"
                        }} else {{
                        sh "git clone {self.repo} theRepo-${{currentBuild.number}} ;echo '+ @show1@ cloning repository'"
                    }}
                }}
                 """]

        pType = self.pType
        if pType:

            print(pType, "type")
            kwargs = {
                "runCommand": self.runCommand,
                "buildCommand": self.buildCommand, "installCommand": self.installCommand,
                "projectDir": self.projectDir, "webServer": self.webServer
            }

            if pType.casefold() == "mysql":
                if not self.kwargs.get("project_id"):
                    code.append(Setup[:2])
                dbDetails = {
                    "userName": self.kwargs.get("userName"),
                    "userPass": self.kwargs.get("userPass"),
                    "rootPass": self.kwargs.get("rootPass"),
                    "parent_id": self.kwargs.get("project_id"),
                    "projectPort": self.projectPort
                }
                code, projectPort = mysqlSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, dbDetails, dbDetails)

            elif pType.casefold() == "mongodb":

                if not self.kwargs.get("project_id"):
                    code.append(Setup[:2])
                dbDetails = {
                    "userName": self.kwargs.get("userName"),
                    "userPass": self.kwargs.get("userPass"),
                    "parent_id": self.kwargs.get("project_id"),
                    "projectPort": self.projectPort
                }
                code, projectPort = mongodbSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, dbDetails)


            elif pType.casefold() == "flask":
                code.append(Setup)
                code, projectPort = pythonSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, "flask", kwargs)

            elif pType.casefold() == "django":
                code.append(Setup)
                code, projectPort = pythonSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, "django", kwargs)
            elif pType.casefold() == "python":
                code.append(Setup)
                code, projectPort = pythonSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, "python", kwargs)


            elif pType.casefold() == "react":
                code.append(Setup)
                code, projectPort = nodeSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, "react", kwargs)

            elif pType.casefold() == "javascript":
                code.append(Setup)
                code, projectPort = nodeSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, "javascript", kwargs)

            elif pType.casefold() == "node":
                code.append(Setup)
                code, projectPort = nodeSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, "node", kwargs)


            elif pType.casefold() == "next":
                # projectPort = 3000
                # Build = ["run next project"]
                # # run container
                # Build.append(
                #     "sudo docker run -d -it" +
                #     f" --name {self.id}-name " +
                #     self.getDEnv(self.envDict) +
                #     " -v \$(pwd)/theRepo-${currentBuild.number}:/app " +
                #     " -w /app " +
                #     f" -p {host_port}:{projectPort} " +
                #     f" --network {self.id}-network-${{currentBuild.number}} " +
                #     " node:18-alpine " +
                #     " sh"
                # )
                # #do instalations
                # Build.append(
                #     f" sudo docker exec {self.id}-name sh -c 'npm install'"
                # )
                # Run = ["Run project"]
                # Run.append(
                #     f"sudo docker exec  -d {self.id}-name sh -c 'HOST=0.0.0.0 npm run dev'"
                # )
                code.append(Setup)
                code, projectPort = nodeSetup(code, self.id, self.Nid,
                                               self.getDEnv(self.envDict),
                                               self.envDict, host_port, "next",kwargs)
        # checkPort = ["skip"]
        # code.append(Setup)
        # code.append(Build)
        # code.append(checkPort)
        # code.append(Run)
        # print(code)
        abort = [
                f'sh "sudo docker rm -f { self.id }-name"'
                # f'sh "sudo docker network rm { self.id }-network"'
        ]
        fail = [
                f'sh "sudo docker rm { self.id }-name -f"'
                # f'sh "sudo docker network rm { self.id }-network"'
        ]
        xml = generate_xml(self.id, code, projectPort, host_port, self.api2Endpoint,
                           True, abort, fail)
        return xml

    def old_data_to_new_repo(self):
        pass

    def get_url(self):
        pass

    def build(self, port, Id=None):
        print('start')
        print(self.generate_xml_config(port))
        print('start')
        if not Id:
            if self.network == "create1":
                # create network using fabric
                return
            try:
                self.server.create_job(
                    f'{self.id}-job', self.generate_xml_config(port)
                )
                self.server.build_job(f"{self.id}-job")
            except Exception as e:
                print("error in creating job")
                raise e
        else:
            self.server.reconfig_job(f"{self.id}-job", self.generate_xml_config(port))
            b = self.server.build_job(Id+'-job')
            print(b)
            print("*********************** build********************")


    def deploy(self):
        pass

    def destroy(self, Id):
        try:
            self.server.delete_job(f'{self.id}-job')
        except Exception as e:
            print(e)
            print("No such job, BOI")

    def create_agent(self):
        pass
