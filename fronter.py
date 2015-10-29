import re, sys
from collections import namedtuple
from getpass import getuser, getpass
from lxml import html

if sys.version_info[0] == 2:
    from urllib2 import HTTPCookieProcessor, HTTPRedirectHandler, build_opener
    from urllib import urlencode
    input = raw_input
else: # Python3
    from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, build_opener
    from urllib.parse import urlencode

from tools import Members, FileTree


class Fronter(object):

    Room = namedtuple('Room', ['name', 'id', 'tools'])

    _imp = {
         3 : 'FileTree',
        18 : 'Members', 
    }

    def __init__(self):

        self.ROOT = 'https://fronter.com'
        self.TARGET = 'https://fronter.com/uio/'

        self.cookie_jar = HTTPCookieProcessor()
        self.opener = build_opener(HTTPRedirectHandler, self.cookie_jar)
        self.rooms = []
        self.login()


    def login(self):

        # Step 1: Get SimpleSAMLSessionID
        #
        #         TARGET -> Service Provider (SP)
        #         SP     -> Identity Provider (IDP) 
        #         IDP requests SAML cookie
        #         Cookie!
        #
        response = self.opener.open(self.TARGET)


        # Step 2: Choose affiliation (UiO)
        response = self.opener.open(response.url + '&org=uio.no')


        # Step 3: Login
        #
        #         IDP -> SP
        #
        # Fetch hidden fields from content
        payload = dict(re.findall('name="(\w+)" value="(.+?)"', response.read().decode('utf-8')))
        # Add username and password
        user = getuser()
        userinput = input('Username: (%s) ' % user)
        self.__user__ = payload['feidename'] = userinput if userinput else user
        self.__secret__ = payload['password'] = getpass()
        data = urlencode(payload).encode('ascii')
        response = self.opener.open(response.url, data)
        
        
        # Step 4: Submit SAMLResponse
        content = response.read().decode('utf-8')
        url = re.findall('action="(.+?)"', content)[0]
        payload = dict(re.findall('name="(\w+)" value="(.+?)"', content))
        data = urlencode(payload).encode('ascii')
        self.opener.open(url, data)
       
 
    def get_rooms(self):
    
        url = self.TARGET + '/adm/projects.phtml'
        response = self.opener.open(url)
        xml = html.fromstring(response.read())
        rooms = xml.xpath('//a[@class="black-link"]')
        self.rooms = [ self.Room(name  = room.text.strip(), 
                                 id    = int(room.get('href').split('=')[-1]), 
                                 tools = []) for room in rooms ]


    def select_room(self, idx):

        room = self.rooms[idx]
        self.roomid = idx
        print(' * %s  <id=%s>' % (room.name, room.id))
        if not room.tools:
            self.get_tools()


    def get_tools(self):
        
        try:
            room = self.rooms[self.roomid]  
            # If we don't do this, we just get the 'toolbar' at the top
            url = self.TARGET + '/contentframeset.phtml?goto_prjid=%i' % room.id
            self.opener.open(url)
            # Read the 'toolbar' on the right hand side
            url = self.TARGET + '/navbar.phtml?goto_prjid=%i' % room.id
            response = self.opener.open(url)
            xml = html.fromstring(response.read())
            tools = xml.xpath('//a[@class="room-tool"]')

            for tool in tools:
                title = tool.xpath('span[@class="tool-title"]')[0].text
                href = tool.get('href')
                toolid = int(re.findall('toolid=([0-9]+)', href)[0])
                if toolid in Fronter._imp:
                    room.tools.append( [ title, Fronter._imp[toolid], href ] )

        except AttributeError:
            print(' !! you must select a room first')
        

    def select_tool(self, idx):

        tool = self.rooms[self.roomid].tools[idx]
        print(' * %s' % tool[0])
        if type(tool[2]) is str:
            tool[2] = globals()[tool[1]](self, self.TARGET + tool[2])
        return tool[2]


    def print_rooms(self):
        for idx, room in enumerate(self.rooms):
            print('[%-3i] %s' % (idx, room.name))

    def print_tools(self):
        for idx, tool in enumerate(self.rooms[self.roomid].tools):
            print('[%-3i] %s' % (idx, tool[0]))
