from getpass import getuser, getpass

from ananas import *
from .plugins import MultipartPostHandler


class Fronter(object):

    Room = namedtuple('Room', ['name', 'id', 'tools'])
    _imp = {
         3 : 'FileTree',
        18 : 'Members', 
        25 : 'RoomInfo'
    }

    def __init__(self):

        org = None
        try:
            conf = ConfigParser()
            conf.read('fronter.conf')
            org = conf.get('fronter', 'org').strip('\'')
        except:
            print(col(' !! [fronter] org not set in fronter.conf', c.ERR))
            raise Exception

        try:
            fsv = conf.getint('fronter', 'studentview')
            self.__studentview__ = 1 if fsv else 0
        except ValueError:
            print(col(' !! [fronter] studentview must be integer (0/1)', c.ERR))
            self.__studentview__ = 0
        except:
            self.__studentview__ = 0

        self.ROOT = 'https://fronter.com'
        self.TARGET = 'https://fronter.com/%s/' % org

        self.cookie_jar = HTTPCookieProcessor()
        self.opener = build_opener(HTTPRedirectHandler, MultipartPostHandler, self.cookie_jar)
        self.login(org)
        self.get_rooms()


    def login(self, org):

        # Step 1: Get SimpleSAMLSessionID
        #
        #         TARGET -> Service Provider (SP)
        #         SP     -> Identity Provider (IDP) 
        #         IDP requests SAML cookie
        #         Cookie!
        #
        response = self.opener.open(self.TARGET)


        # Step 2: Set organization
        response = self.opener.open(response.url + '&org=%s.no' % org)


        # Step 3: Login
        #
        #         IDP -> SP
        #
        # Fetch hidden fields from content
        payload = dict(re.findall('name="(\w+)" value="(.+?)"', response.read().decode('utf-8')))
        # Add username and password
        user = getuser()
        userinput = input('Username: (%s) ' % user)
        payload['feidename'] = self.__user__ = userinput if userinput else user
        payload['password'] = getpass().encode('utf-8')
        # Save it for later use, but encode it just in case lasers, pirates and stupid shit
        self.__secret__ = base64.b64encode(payload['password'])
        data = urlencode(payload).encode('ascii')
        response = self.opener.open(response.url, data)
        
        
        # Step 4: Submit SAMLResponse
        content = response.read().decode('utf-8')
        url = re.findall('action="(.+?)"', content)[0]
        payload = dict(re.findall('name="(\w+)" value="(.+?)"', content))
        data = urlencode(payload).encode('ascii')
        self.opener.open(url, data)
       

    def print_notifications(self):

        url = self.TARGET + '/personal/index.phtml'
        response = self.opener.open(url)
        xml = html.fromstring(response.read())
        table = xml.xpath('//table[contains(@class, "student-notification-element")]')[-1]
        rows = table.getchildren()

        get_text = lambda x: (x.text or x.text_content()).strip()
        fmt = u'{: <16.14}{: <28.26}{: <18.16}{: <18.16}{:>}'
        print(col('\nNotifications:', c.HEAD))
        try:
            print(col(fmt, c.HL).format(*list(map(get_text, rows[0]))))
        except: # No notifications
            print(col(rows[0].text_content(), c.HL))

        for row in rows[1:]:
            print(fmt.format(*list(map(get_text, row))))


    def get_rooms(self):
    
        url = self.TARGET + '/adm/projects.phtml'
        response = self.opener.open(url)
        xml = html.fromstring(response.read())
        rooms = xml.xpath('//a[@class="black-link"]')
        self.rooms = [ self.Room(name  = room.text.strip(), 
                                 id    = int(room.get('href').split('=')[-1]), 
                                 tools = []) for room in rooms ]


    def select_room(self, idx):

        if idx < 1:
            raise IndexError

        room = self.rooms[idx - 1]
        self.roomid = idx - 1
        print(col(' * ', c.ERR) + room.name)
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
                try:
                    href = tool.get('href')
                    toolid = int(re.findall('toolid=([0-9]+)', href)[0]) # IndexError
                    title = tool.xpath('span[@class="tool-title"]')[0].text # TODO: encoding is nuts
                    room.tools.append( [ title, Fronter._imp[toolid], href ] ) # KeyError
                except (IndexError, KeyError):
                    continue

            if not room.tools:
                print(col(' !! no tools available', c.ERR))

            elif self.__studentview__:
                # Reload page with studentview if set in config
                # Sometimes page won't load if not loaded as admin first
                url = self.TARGET + '/contentframeset.phtml?goto_prjid=%i&intostudentview=1' % room.id
                self.opener.open(url)

        except AttributeError: # Should only happen in interactive session
            print(col(' !! you must select a room first', c.ERR))


    def select_tool(self, idx):

        if idx < 1:
            raise IndexError

        tool = self.rooms[self.roomid].tools[idx - 1]
        print(col(' * ', c.ERR) + tool[0])
        if type(tool[2]) is str:
            tool[2] = globals()[tool[1]](self, self.TARGET + tool[2])
        return tool[2]


    def print_rooms(self):
        for idx, room in enumerate(self.rooms):
            print(col('[%-3i] ' % (idx + 1), c.HL) + room.name)


    def print_tools(self):
        for idx, tool in enumerate(self.rooms[self.roomid].tools):
            print(col('[%-3i] ' % (idx + 1), c.HL) + tool[0])
