# magicserver

Functional web server in Python 3.5 using the asyncio module.

## Install

Copy the `server.py` file to your working folder.

## How to use:

Static files have to be enclosed in 'public' directory under root.

```
/
public/
    js/
    img/
    css/
```

To map the dynamic pages, use the function `server.add_route()` which takes 3 parameters

1. HTTP Method.
2. Requested path.
3. Function that would return the dynamic content.

Eg: 

```
def home(request, response):
  return server.send_html_handler(request, response, content)
  
server.add_route('get', '/', home)
```

To start server, use `server.start_server('ip', port)`

Eg:

  `server.start_server("localhost", 8080)`

To send html or json data response, use the following functions `server.send_html_handler()` or `server.send_json_handler()` which take 3 arguments

1. request
2. response
3. requested HTML/JSON content

Eg:
```
def function(request, response):
  return server.send_html_handler(request, response, content)
```
