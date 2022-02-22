# Web application server for a very simple guestbook
import socket
import urllib.parse
import random
import html

# entry - username pair
ENTRIES = [ ('Dauntless','Tobias Eaton'), 
            ('Tribute',"PeetaMellark" )]
# passwords
LOGINS = {"Tobias Eaton": "four",
          "PeetaMellark": "bakery"}

# user side data
SESSIONS = {}

#server_object = HTTPServer(server_address=('', 80), RequestHandlerClass=CGIHTTPRequestHandler)
#server_object.serve_forever()

# function similar to open("path/to/my/socket"); warapper
# 'serv_sock' sort of a ref to the endpoint
serv_sock = socket.socket(
    family=socket.AF_INET, # protocol family set to Internet
    type=socket.SOCK_STREAM, # socket type to stream (i.e. TCP)
    proto=0)                 # set the default protocol
    # proto=socket.IPPROTO_TCP,) 
# reuse the port immediately if the process crashes using SO_REUSEADDR option instead of waiting for a while
serv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
## empty first string - anyone can make connection; port to connect to the server on
## port < 1024 require admin priv?
serv_sock.bind(('127.0.0.1', 8000))
## ready to listen to connections
serv_sock.listen()

'''
POST /submit HTTP/1.0
Host: example.org  ---|\\  headers
Content-Length: 16 ---|//  of the request

name=1&comment=2
'''

def show_comments(session):
    out = "<!doctype html>"
    for entry,who in ENTRIES:
        # html.escape : to prevent XSS attacks where the attacker could include malicious payload
        out += "<p>" + html.escape(entry) + "\n"
        out += "<i>by " + html.escape(who) + "</i></p>"

    # verify if the user is logged in; only logged in users add entries 
    if "user" in session:
        # Cross Site Request Forgery (submitting data once authenticated) mitigation: 
        # to validate if the request for the "entries" is from the same form or an attacker hosted form.
        nonce = str(random.random())[2:]
        session["nonce"] = nonce
        out += "<h1>Hello, " + session["user"] + "</h1>"
        out += "<form action=add method=post>"
        out +=   "<p><input name=guest></p>"
        out += "<link href='http://evilsite.com/styles.css'>"
        out +=   "<p><button>Sign the book!</button></p>"
        out +=   "<input name=nonce type=hidden value=" + nonce + ">"
        out += "</form>"
    else:
        out += "<a href=/login>Sign in to write in the guest book</a>"
    

    return out

# pending implementation of the form data.
def do_request(session,method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", show_comments(session)
    elif method == "POST" and url == "/add":
        params = form_decode(body)
        add_entry(session,params)
        return "200 OK", show_comments(session)
    elif method == "GET" and url == "/login":
        return "200 OK", login_form(session)
    elif method == "POST" and url == "/":
        params = form_decode(body)
        return do_login(session, params)
    else:
        return "404 Not Found", not_found(url, method)

# decodes the POST request which recieved on form submission
def form_decode(body):
    params = {}
    # each atrrb-value pair separated by &
    for field in body.split("&"):
        name, value = field.split("=", 1)
        name = urllib.parse.unquote_plus(name)
        value = urllib.parse.unquote_plus(value)
        params[name] = value
    return params

def do_login(session,params):
    username = params.get("username")
    password = params.get("password")
    if username in LOGINS and LOGINS[username] == password:
        session["user"] = username
        return "200 OK", show_comments(session)
    else:
        out = "<!doctype html>"
        out += "<h1>Invalid password for {}</h1>".format(username)
        return "401 Unauthorized", out

# returning a login form; POST data is sent to /  
def login_form(session):
    body = "<!doctype html>"
    body += "<form action=/ method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body 


def add_entry(session,params):
    if "nonce" not in session or "nonce" not in params: return
    if session["nonce"] != params["nonce"]: return
    if "user" not in session: return
    if 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append((params['guest'], session["user"]))
    return show_comments(session)

def not_found(url, method):
    out = "<!doctype html>"
    out += "<h1>{} {} not found!</h1>".format(method, url)
    return out

# reading the request line by line and interpreting on the go
def handle_connection(client_sock):
    csp = "default-src http://localhost:8000"
    req = client_sock.makefile("b")
    reqline = req.readline().decode()
    print(reqline)
    method, url, version = reqline.split(" ")
    assert method in ["GET", "POST"]

    # storing all the headers of the request in a dict
    headers = {}
    for line in req:
        line = line.decode('utf8')
        # header section ends on a newline
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    # the len(body) in the content will be same as content-length header (used in POST)    
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None

    if "cookie" in headers:
        token = headers["cookie"][len("token="):]
    else:
        # cryptographically unsecure
        token = str(random.random())[2:]

    # setdefault function returns the value of the item with the specified key.
    # for every corresponding token there's a dict for session data
    session = SESSIONS.setdefault(token,{})
    # for generating the desired web page?
    status, body = do_request(session,method, url, headers, body)
    # sending the response back; limited to 1 header, no TLS...
    response = "HTTP/1.0 {}\r\n".format(status)
    print(body)

    # sending the new members the cookie
    if 'cookie' not in headers:
        template = "Set-Cookie: token={}; SameSite=Lax\r\n"
        response += template.format(token)

    # adding the urls from where content access should be allowed
    response += "Content-Security-Policy: {}\r\n".format(csp)
    response += "Content-Length: {}\r\n".format(len(body.encode("utf8")))
    response += "\r\n" + body
    client_sock.sendall(response.encode('utf8'))
    client_sock.close()

while True:
    # waiting for a new connection; socket object returned?
    client_sock, client_addr = serv_sock.accept()
    handle_connection(client_sock)


