from getpass import getuser, getpass

from fronter import *


class Fronter(object):

    Log  = open('fronter.log', 'w')
    Room = namedtuple('Room', ['name', 'id', 'tools'])
    _imp = {
         3 : 'FileTree',
        18 : 'Members', 
        25 : 'RoomInfo',
        43 : 'FileTree',
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
            fsv = conf.getint('admin', 'studentview')
            self.__studentview__ = 1 if fsv else 0
        except ValueError:
            print(col(' !! [admin] studentview must be integer (0/1)', c.ERR))
            self.__studentview__ = 0
        except:
            self.__studentview__ = 0

        self.ROOT = 'https://fronter.com'
        self.TARGET = 'https://fronter.com/%s/' % org

        self.cookie_jar = HTTPCookieProcessor()
        self.opener = build_opener(HTTPRedirectHandler, MultipartPostHandler, self.cookie_jar)
        self.login(org)
        self.get_rooms()


    def post(self, url, payload, **kwargs):
        return self._request('POST', url, payload, **kwargs)

    def get(self, url, **kwargs):
        return self._request('GET', url, **kwargs)

    def get_xml(self, url, **kwargs):
        return self._request('GET', url, xml=True, **kwargs)

    def _request(self, meth, url, payload=None, encoding='ascii', xml=False, find=None, replace=None):

        time = datetime.strftime(datetime.now(), '%H:%M:%S')
        Fronter.Log.write('%s  %-10s %-4s %s\n' % (time, CLASS, meth, url))
        Fronter.Log.flush()

        if payload and encoding:
            payload = urlencode(payload).encode(encoding)
        response = self.opener.open(url, payload)

        if not find and not replace:
            return response if not xml else fromstring(response.read())

        data = response.read()
        to_return = response if not xml else fromstring(data)
        if replace:
            data = data.replace(*replace)
        if find:
            return to_return, re.findall(find, data.decode('utf-8'))

        return to_return

    _request.func_globals['CLASS'] = 'Fronter'


    def get_form(self, xml, name='actionform'):

        forms = xml.xpath('//form')
        form = None
        for f in forms:
            if f.get('name') == name:
                form = f
                break
        else:
            form = forms[0]

        inputs = form.xpath('input[@type="hidden"]')
        payload = dict((i.name, i.get('value')) for i in inputs)

        return payload


    def login(self, org):

        # Step 1: Get SimpleSAMLSessionID
        #
        #         TARGET -> Service Provider (SP)
        #         SP     -> Identity Provider (IDP) 
        #         IDP requests SAML cookie
        #         Cookie!
        #
        response = self.get(self.TARGET)


        # Step 2: Set organization and etch hidden fields from content
        response, payload = self.get(response.url + '&org=%s.no' % org,
                                     find='name="(\w+)" value="(.+?)"')
        payload = dict(payload)


        # Step 3: Login
        #
        #         IDP -> SP
        #
        # Add username and password
        user = getuser()
        userinput = input('Username: (%s) ' % user)
        payload['feidename'] = self.__user__ = userinput if userinput else user
        payload['password'] = getpass().encode('utf-8')
        # Save it for later use, but encode it just in case lasers, pirates and stupid shit
        self.__secret__ = base64.b64encode(payload['password'])
        xml, match = self.post(response.url, payload, xml=True, find='action="(.+?)"')
        url = match[0]
        payload = self.get_form(xml, None)
        
        
        # Step 4: Submit SAMLResponse
        self.post(url, payload)


    def print_notifications(self):

        xml = self.get_xml(self.TARGET + 'personal/index.phtml')
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
    
        xml = self.get_xml(self.TARGET + 'adm/projects.phtml')
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

        tools = self.load_room()
        if not room.tools and not self.parse_tools(tools):
            return False

        return True


    def load_room(self):

        try:
            room = self.rooms[self.roomid]
            # If we don't do this, we just get the 'toolbar' at the top
            url = self.TARGET + 'contentframeset.phtml?goto_prjid=%i' % room.id
            self.get(url)
            # Read the 'toolbar' on the right hand side
            xml = self.get_xml(self.TARGET + 'navbar.phtml?goto_prjid=%i' % room.id)

            if self.__studentview__:
                # Reload page with studentview if set in config
                # Sometimes page won't load if not loaded as admin first
                url = self.TARGET + 'contentframeset.phtml?goto_prjid=%i&intostudentview=1' % room.id
                self.get(url)

            return xml.xpath('//a[@class="room-tool"]')

        except AttributeError: # Should only happen in interactive session
            print(col(' !! you must select a room first', c.ERR))


    def parse_tools(self, tools):

        room = self.rooms[self.roomid]
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
            return False

        return True


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


class MultipartPostHandler(BaseHandler):

    handler_order = HTTPHandler.handler_order - 10

    def http_request(self, request):
        data = request.data
        if data is not None and type(data) != bytes:
            files = []
            header = []
            try:
                try:
                    data = data.items()
                except:
                    pass

                for key, value in data:
                    if hasattr(value, 'fileno'):
                        files.append((key, value))
                    else:
                        header.append((key, value))
            except TypeError:
                return request

            if not files:
                data = urlencode(header)
            else:
                bnd, data = self.multipart_encode(header, files)
                request.add_unredirected_header('Content-Type', 'multipart/form-data; boundary=' + bnd)
            request.data = data

        return request

    def multipart_encode(self, header, files):
        bnd = choose_boundary()

        buffer = ''
        for key, value in header:
            buffer += '--%s\r\n' % bnd
            buffer += 'Content-Disposition: form-data; name="%s"' % key
            buffer += '\r\n\r\n' + value + '\r\n'
        buffer = buffer.encode('utf-8')

        for key, fd in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = fd.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            tmp = '--%s\r\n' % bnd
            tmp += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename)
            tmp += 'Content-Type: %s\r\n' % contenttype
            tmp += '\r\n'

            fd.seek(0)
            buffer += tmp.encode('utf-8')
            buffer += fd.read()
            buffer += '\r\n'.encode('utf-8')

        end = '--%s--\r\n\r\n' % bnd
        buffer += end.encode('utf-8')
        return bnd, buffer

    https_request = http_request
