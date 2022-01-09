# Browser
'''
Pending implementations:                                                         Extra:
1. Cache control (1)                                                             1. Handling quoted attributes (4)      
2. Redirect to another page (1)
3. Compression (1)
4. View Source Code (1) (4)
5. &lt; &gt; --> replace with symbols (1)
6. enable mouse scroll (2)
7. Zooming (2)
8. handling data in script tag (4)
9. Handling comments (4)                                         
'''
import socket
import ssl
import tkinter
import tkinter.font

# common monitor size
WIDTH, HEIGHT = 800,600
# page coordinates
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
# cache (tuple) to keep font style of each word so as to make the browser fast
FONTS = {}
SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
]

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
# building the HTML document tree
# the normal text would have a tag as parent (?)
class Text:
    def __init__(self, text, parent):
        self.text = text
        # text will not have children nodes
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return repr(self.text)

# root node of Layout: setting the properties of the main Document
class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.width = 0
        self.x = 0
        self.y = 0
        self.height = 0
    
    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height + 2*VSTEP
    
    def paint(self, display_list):
        self.children[0].paint(display_list)
        

# interior node for Layout        
# setting the properties of each Element; for items like <div>
class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.width = 0
        self.x = 0
        self.y = 0
        self.height = 0
    
    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)

# code constructs the layout tree from the HTML tree
    def layout(self):
        previous = None
# looping through each child "node" in the Element tree and making a Layout object for each
        self.width = self.parent.width
# align the starting point with parent's left edge
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for child in self.node.children:
            if layout_mode(child) == "inline":
                next = InlineLayout(child, self, previous)
            else:
                next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next
# creating layout tree for each child of the node    
        for child in self.children:
            # width of the child is same as parent
            
            child.layout() # recursive call
        # block's height: tall enough to contain all of its children
        self.height = sum([child.height for child in self.children])

class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
        self.HEAD_TAGS = ["base", "basefont", "bgsound", "noscript","link", "meta", "title", "style", "script",]

    # for adding tags which have been forgotten by the programmer
    def implicit_tags(self, tag):
        # a loop because more than one tag could have been omitted in a row
        while True: 
            open_tags = [node.tag for node in self.unfinished]
            # adding implicit html tag if the first tag added is something else
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            # for head and body tags we needn't close the html tag
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
            # but if tag is smth that comes under head; then add <head> tag 
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            # close head tag before <body> starts
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            # none for </body> and </html> as these are ending ones, added by finish func
            else: 
                break



    def get_attributes(self, text):
    # splitting all the attributes; attribute-value have no whitespace but corner case: content="AAA AAA" is not covered
        parts = text.split()
        tag = parts[0].lower()
        # example for attribute-value pair: name="viewport"
        attributes = {}
        for pair in parts[1:]:
            if "=" in pair:
                key, value = pair.split("=", 1)
                # stripping off the quotes of the value provided it's non-empty value != ""
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.lower()] = value

            else: # for attributes like <input disabled>
                attributes[pair.lower()] = ""
        return tag,attributes

            
    
    def add_text(self, text):
        # referencing the last node that was added to the unfinished list
        if text.isspace(): return
        self.implicit_tags(None) #no implicit tags between text so None
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self,tag):
        # <!doctype html> which doesn't have an ending tag
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag) # check for unifinished tags
        if tag.startswith("/"): # ending node 1 2 3 4
            # no other node to add as parent
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop() # 1 2 3 ; 4
            parent = self.unfinished[-1] # 1 2 3 ; 3
            # children assigned when only finished
            parent.children.append(node) # 3 -> child = [4,...]

        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag,attributes,parent)
            parent.children.append(node)

        else: # for every starting tag
            # if list is empty return None 
            parent = self.unfinished[-1] if self.unfinished else None
            # parent assigned when declared
            node = Element(tag,attributes,parent)
            self.unfinished.append(node)
    
    def finish(self):
        if len(self.unfinished) == 0:
            # this would assign html as root?
            self.add_tag("html")
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()


    def parse(self):
        # iterating each of the character in the body rcvd
        # parses a tree from the </tags>
        page_text = ""
        bracket_start = True
        for text in self.body:
            if(text=='<'):
                bracket_start = True
                if page_text: # append the normal text before starting the brackets as a Text obj
                    self.add_text(page_text)
                    page_text = ""
            elif(text == '>'): # apppend all the text included in tags as a Tags obj
                bracket_start = False
                self.add_tag(page_text)
                page_text = ""
            else: # adding all the text in-between
                    #print(text,end="")
                page_text += text
        if not bracket_start and page_text:
            self.add_text(page_text)
        return self.finish()

class Element:
    def __init__(self,tag,attributes,parent):
        self.tag = tag
        self.children = []
        self.parent = parent
        self.attributes = attributes

    
    def __repr__(self):
        return "<" + self.tag + ">"

# creating layout of how each text is to be shown (inline features)     
# Leaf node of Layout
class InlineLayout:

    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.height = 0
        self.width = self.parent.width
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        

    def flush(self):
        print("hereee")
        if not self.line: return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            y = baseline - self.font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        self.cursor_x = self.x
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

    def paint(self, display_list):
        display_list.extend(self.display_list)

    def layout(self):
        self.display_list = []
        self.line = []
        self.cursor_x = self.x #HSTEP
        self.cursor_y = self.y #VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        self.font = tkinter.font.Font(family="Arial",size=self.size,weight=self.weight,slant=self.style)
        self.recurse(self.node)
        self.flush()
        self.height = self.cursor_y - self.y
    
    
    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
        elif tag == "p":
            self.flush()
        #    self.cursor_y += self.font.metrics("linespace") * 1.25 
        #    self.cursor_x = self.parent.x
        elif 'h1' in tag: #check attributes 'h1 class="title"': title true
            self.flush()
        #    self.cursor_x = HSTEP + WIDTH//4
        #    self.cursor_y += VSTEP + self.font.metrics("ascent") * 1.75
            self.weight = "bold"
    
    def close_tag(self,tag):
        # print("here...{}".format(tag))
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        # as the browser is limited to parsing html we use "small" and "big" here which is replaced by CSS commonly
        # formatting as in chapter 3 skipped for big/small, implementation of self.flush()
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
        #    self.cursor_y += self.y + self.font.metrics("linespace") * 1.25 
        #    self.cursor_x = self.parent.x
        elif "h1" in tag: 
            self.flush()
            #and title == True
        #    self.cursor_x = HSTEP 
        #    self.cursor_y += VSTEP + self.font.metrics("ascent") * 1.75 
            self.weight = "normal"
            #title = False'''

    def recurse(self, tree):

        if isinstance(tree, Text):
            self.text(tree)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)
    

    def text(self,tok):
        #print(tok.text)
        for c in tok.text.split(): #iterationg thru each 'word', removes newlines
            # slows down the browser when computed for every word
            # space = self.font.measure(c) --> measuring the width of text
            font_ = get_font(self.size, self.weight, self.style)
            space = font_.measure(c)
            # checking if complete word can fit in the line
            if (self.cursor_x + space) >= WIDTH - HSTEP or c == "\n":
            # moving to the next line
                self.cursor_y += font_.metrics("linespace") * 1.25   # returning the specific metric 
                # bringing the ptr back to the start
                self.cursor_x = HSTEP
            self.display_list.append((self.cursor_x, self.cursor_y, c,font_))
            self.cursor_x += space + font_.measure(" ")

class Browser:
    def __init__(self):
        # creates a window
        # window -- where the canvas will be displayed
        self.window = tkinter.Tk()
        # to create canvas inside the window (specifications)
        self.canvas = tkinter.Canvas(self.window, width=WIDTH,height=HEIGHT)
        # to position canvas inside window
        self.canvas.pack()
        self.scroll = 0
        # self.scrolldown --> event handler, called when down key is pressed
        # we are binding a function to a key (Tk allows us to do that)
        self.window.bind("<Down>", self.scrolldown)
        #self.window.bind("<MouseWheel>",self.on_mousewheel)
         #weight = bold, slant =italics
    
    def scrolldown(self,something):
        self.scroll += SCROLL_STEP
        self.draw()

    #def on_mousewheel(self,event):
    #    self.canvas.yview_scroll(-1*(event.delta/120), "units")

    # rendering function
    def draw(self): 
        # draw is invoked each time we scroll; thus when we scroll the old text overlaps over the new one
        # thus we delete the previous text before we show the new one
        self.canvas.delete("all")
        #self.canvas.create_rectangle(10, 20, 400, 300)
        #self.canvas.create_oval(100, 100, 150, 150) 
        for x, y, c,f in self.display_list:
        # y --> page coordinate; the user wants to scroll, self.scroll times
        # to get the corresp. screen coordinate we subtract.
        # loading and setting things in create_text takes time  
          if y > self.scroll + HEIGHT: continue # make scrolling faster; else all text is loaded and then adjusted as per the window size (?) 
          if y + VSTEP < self.scroll: continue  # ... here it is skipped
          # x,y coordinates passed to create_text tell where to place the centre of the text
          self.canvas.create_text(x, y - self.scroll, text=c, font=f, anchor = 'nw')
    
    def load(self, hostname):
        headers,body = request(hostname)
        self.nodes = HTMLParser(body).parse()
        #print_tree(self.nodes)
        self.document =  DocumentLayout(self.nodes)
        print_tree(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)
        self.draw()

# distinguish if the Element requires BlockLayout or InilineLayout (text) for layout
def layout_mode(node):
    if isinstance(node, Text):
        return "inline"
    elif node.children:
        for child in node.children:
            if isinstance(child, Text): continue
            if child.tag in BLOCK_ELEMENTS:
                return "block"
        return "inline"
    else:
        return "block"  

def print_tree(node, indent=0):
    # indent being used for just formatting
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

def get_font(size, weight, slant):
    key = (size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(family="Arial",size=size, weight=weight, slant=slant)
        FONTS[key] = font
    return FONTS[key]
            
def request(hostname):
    scheme, hostname = hostname.split("://", 1)

    if "/" in hostname:
        hostname,path = hostname.split("/",1)
        path = "/" + path
    
    s = socket.socket(
        family = socket.AF_INET,
        type = socket.SOCK_STREAM,
        proto = socket.IPPROTO_TCP,
        )
    port = 80
    if ":" in hostname:
        hostname, port = hostname.split(":", 1)
        port = int(port)
    s.connect((hostname,port)) 
    # sending request to the site 
    request_ = b"GET "+ (path).encode() + b" HTTP/1.0\r\n" + b"Host: "+ (hostname).encode() + b"\r\n\r\n"
    s.send(request_)

    # parsing the response
    # making a makefile object (fn of sockets) to receive the objects easily?
    response = s.makefile("r", encoding="utf8", newline="\r\n")
    statusline = response.readline()
    version,status,code = statusline.split(' ')
# assert the status code, print the error message if not right
    assert status == "200", "Got {}: {}".format(status,code)
    headers = {}
    while True:
        line = response.readline()
# 2 "\r\n" => one for newline, one for enter (evrth is complete)
        if line == "\r\n": break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    body = response.read()
    s.close()
    return headers,body

if __name__ == "__main__":
    import sys
    Browser().load(sys.argv[1])
    # loop to ask desktop envt to handle clicks/key presses
    tkinter.mainloop()