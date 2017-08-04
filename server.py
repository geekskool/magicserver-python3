import asyncio
import json
import time
import pprint
import re

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

MIDDLEWARES = []

ALLOWED_ORIGINS = []


def add_route(method, path, func):
    """ADD ROUTES
    Build ROUTES
    """
    path_regex = build_route_regex(path)
    ROUTES[method][path] = (func, path_regex)


def add_middleware(func):
    """ADD middlewares
    """
    MIDDLEWARES.append(func)


def build_route_regex(route):
    route_regex = re.sub(r'(<\w+>)', r'(?P\1.+)', route)
    return re.compile("^{}$".format(route_regex))


def add_allowed_origin(origin):
    """ADD allowed sources
    """
    ALLOWED_ORIGINS.append(origin)


# Server Functions
async def worker(data):
    """WORKER
    Accept requests and invoke request handler
    """
    request = {}
    header_str = data["header"].split("\r\n\r\n")[0]
    if not header_str:
        return err_404_handler(request, {})
    request = header_parser(request, header_str)
    request["body"] = data["content"]
    if request:
        result = await request_handler(request)
        return result


# Parsers
def get_content(request):
    query_string = request["path"].split("?")
    request["path"] = query_string[0]
    content = {}
    for val in query_string[1].split("&"):
        temp = val.split("=")
        content[temp[0]] = temp[1]
    return [request["path"], content]


def get_header(header_list):
    header = {}
    for each_line in header_list:
        key, value = each_line.split(": ", 1)
        header[key] = value
    if "Cookie" in header:
        cookies = header["Cookie"].split(";")
        client_cookies = {}
        for cookie in cookies:
            head, body = cookie.strip().split("=", 1)
            client_cookies[head] = body
            header["Cookie"] = client_cookies
    else:
        header["Cookie"] = ""
    return header


def header_parser(request, header_str):
    """
    HTTP Header Parser
    """
    header_list = header_str.split("\r\n")
    first = header_list.pop(0)
    status_line = first.split()
    request["method"], request["path"], request["protocol"] = status_line
    if "?" in request["path"]:
        request["path"], request["content"] = get_content(request)
    request["header"] = get_header(header_list)
    return request


def form_parser(request):
    """FORM Parser"""
    content_type = request["header"]["Content-Type"]
    boundary = content_type.split("; ")[1]
    request["boundary"] = "--" + boundary.split("=")[1]
    for content in request["body"].split(request["boundary"].encode()):
        form_header_dict = {}
        data = {}
        form_data = content.split(b"\r\n\r\n", 1)
        form_header = form_data[0].split(b"\r\n")
        form_body = ""
        if len(form_data) > 1:
            form_body = form_data[1]
        for each_line in form_header:
            if not each_line or b": " not in each_line:
                continue
            key, value = each_line.split(b": ")
            form_header_dict[key] = value
        if not form_header_dict:
            continue
        form = {}
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
    data_split = body.split("&")
    for val in data_split:
        key, value = val.split("=")
        content_dict[key.decode()] = value.decode()
    return content_dict


# Handler Functions
async def request_handler(request):
    """Request Handler"""
    response = {}
    if "Origin" in request["header"]:
        response = cors_handler(request, response)
    if MIDDLEWARES:
        for middleware in MIDDLEWARES:
            if middleware.PRE:
                request, response = middleware(request, response)
    return method_handler(request, response)


def cors_handler(request, response):
    """CORS Request handler
    handles CORS requests, that
    has a "Origin" header.
    """
    origin = request["header"]["Origin"]
    if origin in ALLOWED_ORIGINS:
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
    return response


def method_handler(request, response):
    """METHOD Handler
    call respective method handler
    """
    METHOD = {
        "GET": get_handler,
        "POST": post_handler,
        "HEAD": head_handler,
        "DELETE": delete_handler,
        "PUT": put_handler,
        "OPTIONS": options_handler
    }
    handler = METHOD[request["method"]]
    return handler(request, response)


def route_match(request, response, ROUTES):
    for func, path_regex in ROUTES.values():
        m = path_regex.match(request["path"])
        if m:
            return func(request, response, **m.groupdict())
    return None


def get_handler(request, response):
    """HTTP GET Handler"""
    try:
        return route_match(request, response, ROUTES["get"])
    except KeyError:
        return static_file_handler(request, response)


def post_handler(request, response):
    """HTTP POST Handler"""
    try:
        content_type = request["header"]["Content-Type"]
        if "multipart" in content_type:
            request = form_parser(request)
            request["content"] = multipart_parser(request)
        elif "json" in content_type:
            request["content"] = json.loads(request["body"].decode())
        else:
            request["content"] = parse_fields(request["body"])
        return route_match(request, response, ROUTES["post"])
    except KeyboardInterrupt:
        return err_404_handler(request, response)


def put_handler(request, response):
    """HTTP PUT Handler"""
    try:
        content_type = request["header"]["Content-Type"]
        if "multipart" in content_type:
            request = form_parser(request)
            request["content"] = multipart_parser(request)
        elif "json" in content_type:
            request["content"] = json.loads(request["body"].decode())
        else:
            request["content"] = parse_fields(request["body"])
        return route_match(request, response, ROUTES["put"])
    except KeyboardInterrupt:
        return err_404_handler(request, response)


def delete_handler(request, response):
    """HTTP DELETE Handler"""
    try:
        return route_match(request, response, ROUTES["delete"])
    except KeyError:
        return err_404_handler(request, response)


def options_handler(request, response):
    """HTTP OPTIONS Handler"""
    path_methods = [i.upper() for i, j in ROUTES.items() if request[
        "path"] in j.keys()]
    response[
        "Access-Control-Allow-Methods"] = ', '.join(path_methods)
    response[
        "Access-Control-Allow-Headers"] = request["header"]["Access-Control-Request-Headers"]
    response["content"] = ""
    return ok_200_handler(request, response)


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


def redirect(request, response, tmp_uri):
    """HTTP 302 handler"""
    response["status"] = "HTTP/1.1 302 Found"
    response["location"] = tmp_uri
    res = response_handler(request, response)
    return res


def response_handler(request, response):
    """HTTP response Handler"""
    response["Date"] = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    response["Connection"] = "close"
    response["Server"] = "magicserver0.2"
    if MIDDLEWARES:
        for middleware in MIDDLEWARES:
            if middleware.POST:
                request, response = middleware(request, response)
    response_string = make_response(response)
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


def make_response(response):
    """
    Make a byte string of the response dictionary
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
    data = {"content": None}
    data["header"] = header.decode()
    pprint.pprint(data["header"])
    if content_length:
        content = await reader.readexactly(content_length)
        data["content"] = content
    response = await worker(data)
    writer.write(response)
    await writer.drain()
    writer.close()


def start_server(hostname, port):
    add_allowed_origin('http://0.0.0.0:{}'.format(port))
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
