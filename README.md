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

To add dynamic routes, put the dynamic part of the route in < > delimiters.

Eg:

```
server.add_route('get', '/user/<username>', user)

def user(request, response, username)
	return server.send_html_handler(request, response, content)
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

## middlewares

Any python object with these attributes suffice as a middleware
1. Has boolean ```self.PRE, self.POST``` values
2. Has a callable with arguments: request, response eg: ```function(request, response)```
3. This callable returns: request, response eg: ```return request, response```

if ```self.PRE = True```, the middleware gets executed in the request handler (before entering the user app)

if ```self.POST = True```, the middleware gets executed in the response handler (after user app, before rendering in browser)


adding a  middleware to server
```
from middlewares import CustomMiddleware
middleware_object = CustomMiddleware()

server.add_middlewares(middleware_object)
```
