from uuid import uuid1
import asyncio
import json
import time
import pprint


ROUTES = {
    "get": {},
    "post": {},
    "put": {},
    "delete": {}
}

CONTENT_TYPE = {
    "html": "text/html",
    "css": "text/css",
    "js": "application/javascript",
    "jpeg": "image/jpeg",
    "jpg": "image/jpg",
    "png": "image/png",
    "gif": "image/gif",
    "ico": "image/x-icon",
    "text": "text/plain",
    "json": "application/json",
    "pdf": "application/pdf"
}

SESSIONS = {}


def add_route(method, path, func):
    """ADD ROUTES
    Build ROUTES
    """
    ROUTES[method][path] = func


# Server Functions
async def worker(data, addr):
    """WORKER
    Accept requests and invoke request handler
    """
    request = {}
    request["address"] = addr
    header_str, body_str = get_http_header(request, data)
    if not header_str:
        return err_404_handler(request, {})
    request = header_parser(request, header_str)
    request["body"] = body_str
    if request:
        result = await request_handler(request)
        return result


# Parsers
def get_http_header(request, data):
    """HTTP Header evaluator
    Accept HTTP header and evaluate
    """
    if b"\r\n\r\n" in data:
        data_list = data.split(b"\r\n\r\n", 1)
        header_str = data_list[0]
        body_str = ""
        if len(data_list) > 1:
            body_str = data_list[1]
        return [header_str, body_str]


def header_parser(request, header_str):
    """
    HTTP Header Parser
    """
    header = {}
    header_list = header_str.split(b"\r\n")
    first = header_list.pop(0)
    status_line = [x.decode() for x in first.split()]
    request["method"], request["path"], request["protocol"] = status_line
    if "?" in request["path"]:
        query_string = request["path"].split("?")
        request["path"] = query_string[0]
        content = {}
        for val in query_string[1].split("&"):
            temp = val.split("=")
            content[temp[0]] = temp[1]
        request["content"] = content
    for each_line in header_list:
        key, value = each_line.split(b": ", 1)
        header[key] = value
    if b"Cookie" in header:
        cookies = header[b"Cookie"].split(b";")
        client_cookies = {}
        for cookie in cookies:
            head, body = cookie.strip().split(b"=", 1)
            client_cookies[head] = body
        header[b"Cookie"] = client_cookies
    else:
        header[b"Cookie"] = ""
    request["header"] = header
    return request


def form_parser(request):
    """FORM Parser"""
    form = {}
    content_type = request["header"][b"Content-Type"]
    boundary = content_type.split(b"; ")[1]
    request["boundary"] = b"--" + boundary.split(b"=")[1]
    for content in request["body"].split(request["boundary"]):
        form_header_dict = {}
        data = {}
        if not content:
            continue
        form_data = content.split(b"\r\n\r\n", 1)
        form_header = form_data[0].split(b"\r\n")
        form_body = ""
        if not form_header:
            continue
        if len(form_data) > 1:
            form_body = form_data[1]
        for each_line in form_header:
            if not each_line or b": " not in each_line:
                continue
            key, value = each_line.split(b": ")
            form_header_dict[key] = value
        if not form_header_dict:
            continue
        for each_item in form_header_dict[b"Content-Disposition"].split(b"; "):
            if b"=" in each_item:
                name, value = each_item.split(b"=", 1)
                data[name] = value.strip(b'"')
                data["body"] = form_body
                form[data[b"name"]] = data
    request["form"] = form
    return request


def multipart_parser(request):
    content_dict = {}
    for key, value in request["form"].items():
        if b"filename" not in value:
            content_dict[key.decode()] = value["body"].decode()
        else:
            content_dict[key.decode()] = value["body"]
    return content_dict


def parse_fields(body):
    content_dict = {}
    data_split = body.split(b"&")
    for val in data_split:
        key, value = val.split(b"=")
        content_dict[key.decode()] = value.decode()
    return content_dict

# Handler Functions


async def request_handler(request):
    """Request Handler"""
    response = {}
    response = session_handler(request, response)
    return method_handler(request, response)


def session_handler(request, response):
    """Session Handler
    Add session ids to SESSION
    """
    browser_cookies = request["header"][b"Cookie"]
    if (browser_cookies and b"sid" in browser_cookies and
            browser_cookies[b"sid"].decode() in SESSIONS):
        return response
    cookie = str(uuid1())
    response["Set-Cookie"] = "sid=" + cookie
    SESSIONS[cookie] = {}
    return response


def method_handler(request, response):
    """METHOD Handler
    call respective method handler
    """
    handler = METHOD[request["method"]]
    return handler(request, response)


def get_handler(request, response):
    """HTTP GET Handler"""
    try:
        return ROUTES["get"][request["path"]](request, response)
    except KeyError:
        return static_file_handler(request, response)


def post_handler(request, response):
    """HTTP POST Handler"""
    try:
        if b"multipart" in request["header"][b"Content-Type"]:
            request = form_parser(request)
            request["content"] = multipart_parser(request)
        else:
            request["content"] = parse_fields(request["body"])
        return ROUTES["post"][request["path"]](request, response)
    except KeyboardInterrupt:
        return err_404_handler(request, response)


def put_handler(request, response):
    """HTTP PUT Handler"""
    try:
        if b"multipart" in request["header"][b"Content-Type"]:
            request = form_parser(request)
            request["content"] = multipart_parser(request)
        else:
            request["content"] = parse_fields(request["body"])
        return ROUTES["put"][request["path"]](request, response)
    except KeyboardInterrupt:
        return err_404_handler(request, response)


def delete_handler(request, response):
    """HTTP DELETE Handler"""
    try:
        return ROUTES["delete"][request["path"]](request, response)
    except KeyError:
        return err_404_handler(request, response)


def head_handler(request, response):
    """HTTP HEAD Handler"""
    get_handler(request, response)
    response["content"] = ""
    return response_handler(request, response)


def static_file_handler(request, response):
    """HTTP Static File Handler"""
    try:
        with open("./public" + request["path"], "rb") as file_descriptor:
            res = file_descriptor.read()
    except IOError:
        return err_404_handler(request, response)
    except FileNotFoundError:
        res = b""
    response["content"] = res
    content_type = request["path"].split(".")[-1].lower()
    response["Content-type"] = CONTENT_TYPE[content_type]
    return ok_200_handler(request, response)


def err_404_handler(request, response):
    """HTTP 404 Handler"""
    response["status"] = "HTTP/1.1 404 Not Found"
    response["content"] = "Content Not Found"
    response["Content-type"] = "text/HTML"
    return response_handler(request, response)


def ok_200_handler(request, response):
    """HTTP 200 Handler"""
    response["status"] = "HTTP/1.1 200 OK"
    if response["content"] and response["Content-type"]:
        response["Content-Length"] = str(len(response["content"]))
    res = response_handler(request, response)
    return res


def response_handler(request, response):
    """HTTP response Handler"""
    response["Date"] = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    response["Connection"] = "close"
    response["Server"] = "magicserver0.2"
    response_string = response_stringify(response)
    return response_string


def send_html_handler(request, response, content):
    """send_html handler
    Add html content to response
    """
    if content:
        response["content"] = content
        response["Content-type"] = "text/html"
        res = ok_200_handler(request, response)
        return res
    else:
        return err_404_handler(request, response)


def send_json_handler(request, response, content):
    """send_json handler
    Add JSON content to response
    """
    if content:
        response["content"] = json.dumps(content)
        response["Content-type"] = "application/json"
        return ok_200_handler(request, response)
    else:
        return err_404_handler(request, response)


# Session Managers


def add_session(request, content):
    """ADD SESSION
    Add session id to SESSIONS
    """
    browser_cookies = request["header"][b"Cookie"]
    if b"sid" in browser_cookies:
        sid = browser_cookies[b"sid"].decode()
        if sid in SESSIONS:
            SESSIONS[sid] = content


def get_session(request):
    """GET SESSION
    Get session id from SESSIONS
    """
    browser_cookies = request["header"][b"Cookie"]
    if browser_cookies and b"sid" in browser_cookies:
        sid = browser_cookies[b"sid"].decode()
        if sid in SESSIONS:
            return SESSIONS[sid]


def del_session(request):
    """DEL SESSIONS
    Delete session from SESSIONS
    """
    browser_cookies = request["header"][b"Cookie"]
    if b"sid" in browser_cookies:
        sid = browser_cookies[b"sid"].encode()
        if sid in SESSIONS:
            del SESSIONS[sid]


# Stringify
def response_stringify(response):
    """
    Stringify the response object
    """
    response_string = response["status"] + "\r\n"
    keys = [key for key in response if key not in ["status", "content"]]
    for key in keys:
        response_string += key + ": " + response[key] + "\r\n"
    response_string += "\r\n"
    response_string = response_string.encode()
    if "content" in response:
        content = response["content"]
        if isinstance(content, str):
            content = content.encode()
        new_line = b"\r\n\r\n"
        response_string += content + new_line
    return response_string


METHOD = {
    "GET": get_handler,
    "POST": post_handler,
    "HEAD": head_handler,
    "DELETE": delete_handler,
    "PUT": put_handler
}


def check_content(headers):
    if b"Content-Length" in headers:
        con_pos = headers.find(b"Content-Length")
        col_pos = headers.find(b":", con_pos)
        srsn = headers.find(b"\r\n", col_pos)
        con_len = int(headers[col_pos + 2:srsn])
        return con_len

async def handle_connections(reader, writer):
    addr = writer.get_extra_info("peername")
    print("Connection from:{0}".format(addr))
    header = await reader.readuntil(b"\r\n\r\n")
    content_length = check_content(header)
    data = header
    pprint.pprint(header.decode())
    if content_length:
        content = await reader.readexactly(content_length)
        data += content
    response = await worker(data, addr)
    writer.write(response)
    await writer.drain()
    writer.close()


def start_server(hostname, port):
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(handle_connections, hostname, port, loop=loop)
    server = loop.run_until_complete(coro)
    print("Serving on {0}".format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
