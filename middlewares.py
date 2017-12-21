from uuid import uuid1

class Session:
    """Session middleware class
    """
    def __init__(self):
        self.SESSIONS = {}
        self.PRE = True
        self.POST = False

    def __call__(self, *args):
        return self.session_middleware(*args)

    def session_middleware(self, request, response):
        """Add session ids to self.SESSION
        """
        browser_cookies = request["header"]["Cookie"]
        if (browser_cookies and "sid" in browser_cookies and
                browser_cookies["sid"] in self.SESSIONS):
            return request, response
        cookie = str(uuid1())
        response["Set-Cookie"] = "sid=" + cookie
        self.SESSIONS[cookie] = {}
        return request, response

    def add_session(self, request, content):
        """ADD SESSION
        Add session id to self.SESSIONS
        """
        browser_cookies = request["header"]["Cookie"]
        if "sid" in browser_cookies:
            sid = browser_cookies["sid"]
            if sid in self.SESSIONS:
                self.SESSIONS[sid] = content


    def get_session(self, request):
        """GET SESSION
        Get session id from self.SESSIONS
        """
        browser_cookies = request["header"]["Cookie"]
        if browser_cookies and "sid" in browser_cookies:
            sid = browser_cookies["sid"]
            if sid in self.SESSIONS:
                return self.SESSIONS[sid]

    def del_session(self, request):
        """DEL SESSIONS
        Delete session from self.SESSIONS
        """
        browser_cookies = request["header"]["Cookie"]
        if "sid" in browser_cookies:
            sid = browser_cookies["sid"]
            if sid in self.SESSIONS:
                del self.SESSIONS[sid]


class Logger:
    """Logger middleware
    Logs all request, response to a file
    """
    def __init__(self, DEBUG=False, FILENAME="magicserver.log"):
        self.PRE = False
        self.POST = True
        self.DEBUG = DEBUG
        self.FILENAME = FILENAME

    def __call__(self, *args):
        return self.logger(*args)

    def logger(self, request, response):
        ip = request["header"]["Host"].split(":")[0]
        date = response["Date"]
        method = request["method"]
        path = request["path"]
        status = response["status"]

        log = "{} - - [{}] \"{} {}\" {}\n".format(ip, date, method,
                                                  path, status)
        self.write_print_logs(log)
        return request, response

    def write_print_logs(self, log):
        if self.DEBUG:
            print(log, end="")
        with open(self.FILENAME, mode="a") as log_data:
            log_data.write(log)
