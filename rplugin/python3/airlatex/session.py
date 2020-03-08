import pynvim
import browser_cookie3
import requests
import json
import time
from threading import Thread, currentThread
from queue import Queue
import re
from airlatex.project_handler import AirLatexProject
from airlatex.util import _genTimeStamp, getLogger
# from project_handler import AirLatexProject # FOR DEBUG MODE
# from util import _genTimeStamp # FOR DEBUG MODE



import traceback
def catchException(fn):
    def wrapped(self, nvim, *args, **kwargs):
        try:
            return fn(self, nvim, *args, **kwargs)
        except Exception as e:
            self.log.exception(str(e))
            nvim.err_write(str(e)+"\n")
            raise e
    return wrapped


### All web page related airlatex stuff
class AirLatexSession:
    def __init__(self, domain, servername, sidebar):
        self.sidebar = sidebar
        self.servername = servername
        self.domain = domain
        self.url = "https://"+domain
        self.authenticated = False
        self.httpHandler = requests.Session()
        self.cached_projectList = []
        self.projectThreads = []
        self.status = ""
        self.menu = []
        self.log = getLogger(__name__)

    @catchException
    def cleanup(self, nvim):
        self.log.debug("cleanup()")
        for p in self.cached_projectList:
            if "handler" in p:
                p["handler"].disconnect()
        for t in self.projectThreads:
            t.do_run = False
        self.projectThreads = []

    @catchException
    def login(self, nvim):
        self.log.debug("login()")
        if not self.authenticated:
            self.cj = browser_cookie3.load()
            self.updateStatus(nvim, "Connecting")
            # check if cookie found by testing if projects redirects to login page
            try:
                redirect  = self.httpHandler.get(self.url + "/projects", cookies=self.cj)
                if len(redirect.history) == 0:
                    self.authenticated = True
                    self.updateProjectList(nvim)
                    return True
                else:
                    self.authenticated = False
                    return False
            except Exception as e:
                self.authenticated = False
                self.updateStatus(nvim, "Connection failed: "+str(e))
        else:
            return False

    # Returns a list of airlatex projects
    # @catchException
    def projectList(self):
        return self.cached_projectList

    @catchException
    def updateProjectList(self, nvim):
        self.log.debug("updateProjectList()")
        if self.authenticated:

            def loading(self,nvim):
                if not nvim:
                    nvim = pynvim.attach("socket",path=self.servername)
                i = 0
                t = currentThread()
                while getattr(t, "do_run", True):
                    s = " .." if i%3 == 0 else ". ." if i%3 == 1 else ".. "
                    self.updateStatus(nvim, s+" Loading "+s)
                    i += 1
                    time.sleep(0.1)
            thread = Thread(target=loading, args=(self,nvim), daemon=True)
            thread.start()

            projectPage = self.httpHandler.get(self.url + "/project").text
            thread.do_run = False
            pos_script_1  = projectPage.find("<script id=\"data\"")
            pos_script_2 = projectPage.find(">", pos_script_1 + 20)
            pos_script_close = projectPage.find("</script", pos_script_2 + 1)
            if pos_script_1 == -1 or pos_script_2 == -1 or pos_script_close == -1:
                self.menu = [
                    "Error: Cannot login to:", "    "+self.domain,
                    "Did you login first in your Browser?",
                    "   (Firefox or Chrome)",
                    "",
                    ("press [O] to open browser","openbrowser"),
                    ("press [R] to retry connecting","reconnect")
                ]
                self.authenticated = False
                self.updateStatus(nvim, "Offline. Please Login.")
                self.triggerRefresh(nvim)
                return []
            data = projectPage[pos_script_2+1:pos_script_close]
            data = json.loads(data)
            self.user_id = re.search("user_id\s*:\s*'([^']+)'",projectPage)[1]
            self.updateStatus(nvim, "Online")

            self.cached_projectList = data["projects"]
            self.cached_projectList.sort(key=lambda p: p["lastUpdated"], reverse=True)
            self.triggerRefresh(nvim)

    # Returns a list of airlatex projects
    @catchException
    def connectProject(self, nvim, project):
        if self.authenticated:

            # This is needed because IOLoop and pynvim interfere!
            msg_queue = Queue()
            msg_queue.put(("msg",None,"Connecting Project"))
            project["msg_queue"] = msg_queue
            def flush_queue(queue, project, servername):
                t = currentThread()
                nvim = pynvim.attach("socket",path=servername)
                while getattr(t, "do_run", True):
                    cmd, doc, data = queue.get()
                    try:
                        if cmd == "msg":
                            self.log.debug("msg_queue : "+data)
                            project["msg"] = data
                            nvim.command("call AirLatex_SidebarRefresh()")
                            continue
                        elif cmd == "await":
                            project["await"] = data
                            nvim.command("call AirLatex_SidebarRefresh()")
                            continue
                        elif cmd == "refresh":
                            self.triggerRefresh(nvim)
                            continue

                        buf = doc["buffer"]
                        self.log.debug("cmd="+cmd)
                        if cmd == "applyUpdate":
                            buf.applyUpdate(data)
                        elif cmd == "write":
                            buf.write(data)
                        elif cmd == "updateRemoteCursor":
                            buf.updateRemoteCursor(data)
                    except Exception as e:
                        self.log.error("Exception"+str(e))
                        project["msg"] = "Exception:"+str(e)
                        nvim.command("call AirLatex_SidebarRefresh()")
            msg_thread = Thread(target=flush_queue, args=(msg_queue, project, self.servername), daemon=True)
            msg_thread.start()
            self.projectThreads.append(msg_thread)

            # start connection
            def initProject():
                nvim = pynvim.attach("socket",path=self.servername)
                try:
                    AirLatexProject(self._getWebSocketURL(), project, self.user_id, msg_queue, msg_thread)
                except Exception as e:
                    self.log.error(traceback.format_exc(e))
                    nvim.err_write(traceback.format_exc(e)+"\n")
            thread = Thread(target=initProject,daemon=True)
            self.projectThreads.append(thread)
            thread.start()

    @catchException
    def updateStatus(self, nvim, msg):
        self.log.debug_gui("updateStatus("+msg+")")
        self.status = msg
        nvim.command("call AirLatex_SidebarUpdateStatus()")

    @catchException
    def triggerRefresh(self, nvim):
        self.log.debug_gui("triggerRefresh()")
        nvim.command("call AirLatex_SidebarRefresh()")

    def _getWebSocketURL(self):
        if self.authenticated:
            # Generating timestamp
            timestamp = _genTimeStamp()

            # To establish a websocket connection
            # the client must query for a sec url
            self.httpHandler.get(self.url + "/project")
            channelInfo = self.httpHandler.get(self.url + "/socket.io/1/?t="+timestamp)
            wsChannel = channelInfo.text[0:channelInfo.text.find(":")]
            return "wss://" + self.domain + "/socket.io/1/websocket/"+wsChannel



# for debugging
if __name__ == "__main__":
    import asyncio
    from mock import Mock
    import os
    DOMAIN = os.environ["DOMAIN"]
    sidebar = Mock()
    nvim = Mock()
    pynvim = Mock()
    async def main():
        sl = AirLatexSession(DOMAIN, None, sidebar)
        sl.login(nvim)
        project = sl.projectList()[1]
        print(">>>>",project)
        sl.connectProject(nvim, project)
        time.sleep(3)
        # print(">>>",project)
        doc = project["rootFolder"][0]["docs"][0]
        project["handler"].joinDocument(doc)
        time.sleep(6)
        print(">>>> sending ops")
        # project["handler"].sendOps(doc, [{'p': 0, 'i': '0abB\n'}])
        # project["handler"].sendOps(doc, [{'p': 0, 'i': 'def\n'}])
        # project["handler"].sendOps(doc, [{'p': 0, 'i': 'def\n'}])

    asyncio.run(main())
