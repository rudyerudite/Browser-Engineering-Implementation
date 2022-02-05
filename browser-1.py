# Browser
'''
Pending implementations:                                                         Extra:
1. Cache control (1)                                                             1. Handling quoted attributes (4)      
2. Redirect to another page (1)                                            not clear with TagSelector/ Descendant
3. Compression (1)                                                                
4. View Source Code (1) (4)
5. &lt; &gt; --> replace with symbols (1)
6. enable mouse scroll (2)
7. Zooming (2)
8. handling data in script tag (4)
9. Handling comments (4)   
10. Implement a scrolldown bar,bullets to list items (5)                                      
'''

''' Layout Tree
DocumentLayout
  BlockLayout (html element)                    
    InlineLayout (body element)
      LineLayout (first line of text)
        TextLayout ("Here")
        TextLayout ("is")
        TextLayout ("some")
        TextLayout ("text")
        TextLayout ("that")
        TextLayout ("is")
    LineLayout (second line of text)
        TextLayout ("spread")
        TextLayout ("across")
        TextLayout ("multiple")
        TextLayout ("lines")

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

# allowed properties which a child can inherit from parent; bg-color not allowed...
INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}
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

# CSS limited to bg colors...
# CSS maintains a cascade order to determine which rules take priority, and when one rule overrides another. 
# Browser declarations < User normal declarations < Author normal declarations < Author important declarations < User important declarations
        
# selecting properties wrt a tag; p selecting properties of <p> tag
class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        # cascade order as per tag, more priority to self rules (?)
        self.priority = 1
    
    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority
    
    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False

    


# CSS parser for parsing the property:value pair in attributes
class CSSParser:
    def __init__(self, s):
    # text being parsed
        self.s = s
    # current position 
        self.i = 0
    
    # parsing whitespaces
    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    # parsing the properties:(whitespace)value [property names (which use letters and the dash), 
    #                               numbers (which use the minus sign, numbers, periods), 
    #                               units (the percent sign), and colors (which use the hash sign).]
    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        assert self.i > start
        return self.s[start:self.i]

# to check for a punctuation/literal character
    def literal(self, literal):
        assert self.i < len(self.s) and self.s[self.i] == literal
        self.i += 1

    def pair(self):
        prop = self.word()
        self.whitespace() #not required?
        self.literal(":")
        self.whitespace()
        val = self.word()
        return prop.lower(), val

# creating a dictionary of all the properties
    def body(self): # LL(1) parser ??
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                pairs[prop.lower()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except AssertionError:
            # moving ahead with the next property if there's some error in b/w
                self.i += 1
                why = self.ignore_until([";","}"]) 
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs
   
    # used for ignoring program errors?
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1

    def selector(self):
        out = TagSelector(self.word().lower())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.lower())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except AssertionError:
                self.i += 1
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules

# Implement the DrawText command
class DrawText:
    def __init__(self, x1, y1, text, font,color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")
        self.color = color
    
    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw',
            fill=self.color,
        )

# Ipmlement the DrawRect command :  background to the text
class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        
    
    def execute(self, scroll, canvas):
        canvas.create_rectangle(  #By default, create_rectangle draws a one-pixel black border, which for backgrounds we don’t want, so width = 0
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color,
        )

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
        self.width = self.parent.width
# align the starting point with parent's left edge
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
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
        
    # creating a new line
    def new_line(self):
        self.previous_word = None
        self.cursor_x = self.x
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)


    def paint(self, display_list):
        bgcolor = self.node.style.get("background-color","transparent")

        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            display_list.append(rect)


        for child in self.children:
            child.paint(display_list)

    
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x
       
        if self.previous:
            self.y = self.previous.y + self.previous.height
            #print(self.previous.node)
        else:
            self.y = self.parent.y

        self.new_line()        
        self.recurse(self.node)
        for line in self.children:
            line.layout()
        self.height = sum([line.height for line in self.children])


    def recurse(self, node):
        if isinstance(node, Text):
            self.text(node)
        else:
            if node.tag == "br":
                self.new_line()
            for child in node.children:
                self.recurse(child)

    def text(self,node):
        #print(tok.text)
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": #conversion to Tk format
            style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font_ = get_font(size, weight, style)

        for c in node.text.split(): #iterationg thru each 'word', removes newlines
            # space = self.font.measure(c) --> measuring the width of text
            self.font = font_
            space = font_.measure(c)
            # checking if complete word can fit in the line
            if (self.cursor_x + space) >= self.width - HSTEP:
            # moving to the next line
                self.new_line()
            line = self.children[-1]
            text = TextLayout(node, c, line, self.previous_word)
            line.children.append(text)
            self.previous_word = text
            #self.display_list.append((self.cursor_x, self.cursor_y, c,font_))
            self.cursor_x += space + font_.measure(" ")

# for each line break
# children of InlineLayout (body element)
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        

        if not self.children:
            self.height = 0
            return
        # laying out each word
        for word in self.children:
            word.layout()

        max_ascent = max([word.font.metrics("ascent")
                  for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        # computing the y field
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent") for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)

    

# for each "word"
# children on LineLayout
class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)
        # positioning each word that is a part of a line (y already computed)
        self.width = self.font.measure(self.word)
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(DrawText(self.x, self.y, self.word, self.font, color))
           

class Browser:
    def __init__(self):
        # creates a window
        # window -- where the canvas will be displayed
        self.window = tkinter.Tk()
        # to create canvas inside the window (specifications)
        self.canvas = tkinter.Canvas(self.window, width=WIDTH,height=HEIGHT,bg="white")
        # to position canvas inside window
        self.canvas.pack()
        self.scroll = 0
        # self.scrolldown --> event handler, called when down key is pressed
        # we are binding a function to a key (Tk allows us to do that)
        self.window.bind("<Down>", self.scrolldown)
        # left click bind
        self.window.bind("<Button-1>", self.click)
        self.display_list = []
        self.url = None
        #self.window.bind("<MouseWheel>",self.on_mousewheel)
         #weight = bold, slant =italics
        with open("C:\\Users\\Shruti Dixit\\Documents\\Browser-Code\\browser.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()
    

    def scrolldown(self,eventobject):
        max_y = self.document.height - HEIGHT
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()

    # event handler is passed an event object
    def click(self, e):
        # y coordinates are relative to the browser window; top-left
        x, y = e.x, e.y
        # adding current scroll value
        y += self.scroll
        # finding a link in the current area where the link is clicked
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: 
            return
        print(objs)
        elt = objs[-1].node
        print(elt)

        # finding the URL of the text element... climbing back the HTML tree until the tag is found
        # implementing viewing the pages of clicked links
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = resolve_url(elt.attributes["href"], self.url)
                return self.load(url)
            elt = elt.parent



    # rendering function
    def draw(self): 
        # draw is invoked each time we scroll; thus when we scroll the old text overlaps over the new one
        # thus we delete the previous text before we show the new one
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)

    
    def load(self, hostname):
        headers,body = request(hostname)
        self.nodes = HTMLParser(body).parse()
        # copy() function creates a shallow copy
        rules = self.default_style_sheet.copy()
        self.url = hostname
        # browser will have to find the link for the sheets <link rel="stylesheet" href="/main.css"> and apply them
        links = [node.attributes["href"]
             for node in tree_to_list(self.nodes, [])
             if isinstance(node, Element)
             and node.tag == "link"
             and "href" in node.attributes
             and node.attributes.get("rel") == "stylesheet"]

        for link in links:
            try:
                header, body = request(resolve_url(link, hostname))
            except:
                continue
        rules.extend(CSSParser(body).parse())
        style(self.nodes,sorted(rules, key=cascade_priority))
        #print_tree(self.nodes)
        self.document =  DocumentLayout(self.nodes)
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

def cascade_priority(rule):
    # body contains the exact attributes, selector =  Tag/Descendant object
    selector, body = rule
    return selector.priority

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

def style(node,rules):
    node.style = {}

    # setting inherited properties in case 
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value

    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            computed_value = compute_style(node, property, value)
            if not computed_value: continue #font-size returns None if wrong format
            node.style[property] = computed_value

    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            node.style[property] = value

    for child in node.children:
        style(child,rules)

# re-sizing the font-size as per %age and px; computed font-size is converted to px 
# %age scenarios: the size of the font is %age time more
def compute_style(node, property, value):
    if property == "font-size":
        if value.endswith("px"):
            return value
        elif value.endswith("%"):
            if node.parent:
                parent_font_size = node.parent.style["font-size"]
            else:
                parent_font_size = INHERITED_PROPERTIES["font-size"]
            node_pct = float(value[:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            return str(node_pct * parent_px) + "px"
        else:
            return None
    else:
        return value

def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list

# returning the full URL of the stylesheet
def resolve_url(url, current):
    # for normal URLs
    if "://" in url:
        return url
    
    # for host-relative URLs
    elif url.startswith("/"):
        scheme, hostpath = current.split("://", 1)
        host, oldpath = hostpath.split("/", 1)
        return scheme + "://" + host + url

    # for path-relative URLs (change to specific directory)
    else:
        dir, _ = current.rsplit("/", 1)
        while url.startswith("../"):
            url = url[3:]
            # check for slashes in scheme ://
            if dir.count("/") == 2: continue
            dir, _ = dir.rsplit("/", 1)
        return dir + "/" + url
    

    

if __name__ == "__main__":
    import sys
    Browser().load(sys.argv[1])
    # loop to ask desktop envt to handle clicks/key presses
    tkinter.mainloop()