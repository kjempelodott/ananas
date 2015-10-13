#!/usr/bin/env python

import re, sys
from urllib2 import HTTPCookieProcessor, HTTPRedirectHandler, build_opener
from urllib import urlencode
from getpass import getuser, getpass
from lxml import html


class Client:

    TARGET = 'https://fronter.com/uio/'

    def __init__(self):
        self.actions = {'help' : self.print_actions,
                        'return' : self.back}

    def print_actions(self, *_):
        print('actions: ' + ' | '.join(self.actions))

    def back(self, *_):
        sys.exit(0)


class Deltakere(Client, object):

    def __init__(self, mother, url):

        super(Deltakere, self).__init__()
        self.mother = mother
        self.opener = mother.opener

        self.actions['members']       = self.print_members, 
        self.actions['select-member'] = self.select_member,
        self.scrape_members(url)
        self.print_actions()

    def scrape_members(self, url):
        pass

    def print_members(self):
        pass

    def select_member(self):
        pass

    def back(self, *_):
        return self.mother
        

class Rapportinnlevering(Client, object):

    def __init__(self, mother, url):

        super(Rapportinnlevering, self).__init__()
        self.mother = mother
        self.opener = mother.opener

    def back(self, *_):
        return self.mother


class Fronter(Client, object):

    _imp = ('Deltakere', 'Rapportinnlevering')

    def __init__(self):

        super(Fronter, self).__init__()
        self.cookie_jar = HTTPCookieProcessor()
        self.opener = build_opener(HTTPRedirectHandler, self.cookie_jar)
        self.rooms = []
        self.tools = []
        self._rooms = None

        self.actions['rooms']       = self.print_rooms
        self.actions['select-room'] = self.select_room
        self.actions['tools']       = self.print_tools
        self.actions['select-tool'] = self.select_tool


    def login(self):

        # Step 1: Get SimpleSAMLSessionID
        #
        #         TARGET -> Service Provider (SP)
        #         SP     -> Identity Provider (IDP) 
        #         IDP requests SAML cookie
        #         Cookie!
        #
        response = self.opener.open(Fronter.TARGET)


        # Step 2: Choose affiliation (UiO)
        response = self.opener.open(response.url + '&org=uio.no')


        # Step 3: Login
        #
        #         IDP -> SP
        #
        # Fetch hidden fields from content
        payload = dict(re.findall('name="(\w+)" value="(.+?)"', response.read()))
        # Add username and password
        user = getuser()
        userinput = raw_input('Username: (%s) ' % user)
        payload['feidename'] = userinput if userinput else user
        payload['password'] = getpass()
        data = urlencode(payload).encode('ascii')
        response = self.opener.open(response.url, data)
        
        
        # Step 4: Submit SAMLResponse
        content = response.read()
        url = re.findall('action="(.+?)"', content)[0]
        payload = dict(re.findall('name="(\w+)" value="(.+?)"', content))
        data = urlencode(payload).encode('ascii')
        response = self.opener.open(url, data)
       
 
    def get_rooms(self):
    
        url = Fronter.TARGET + '/adm/projects.phtml'
        response = self.opener.open(url)
        tree = html.fromstring(response.read())
        rooms = tree.xpath('//a[@class="black-link"]')
        self.rooms = [(room.text.strip(), int(room.get('href').split('=')[-1])) 
                      for room in rooms]


    def scrape_room(self):

        try:
            # If we don't do this, we just get the 'toolbar' at the top
            url = Fronter.TARGET + '/contentframeset.phtml?goto_prjid=%i' % self._room[1]
            self.opener.open(url)
            # Read the 'toolbar' on the right hand side
            url = Fronter.TARGET + '/navbar.phtml?goto_prjid=%i' % self._room[1]
            response = self.opener.open(url)
            tree = html.fromstring(response.read())
            tools = tree.xpath('//a[@class="room-tool"]')
            self.tools = []

            for tool in tools:
                title = tool.xpath('span[@class="tool-title"]')[0].text
                if title in Fronter._imp:
                    self.tools.append((title, tool.get('href')))

        except AttributeError:
            print(' !! you must select a room first')
        
                
    def select_room(self, idx):
        try:
            if not self.rooms:
                self.get_rooms()

            self._room = self.rooms[idx]
            print(' .. %s <id=%s>' % self._room)
            self._tool = None

        except IndexError:
            print(' !! index out of range')


    def select_tool(self, idx):
        try:
            if not self.tools:
                self.scrape_room()

            self._tool = self.tools[idx]
            print(' .. %s' % self._tool[0])
            return globals()[self._tool[0]](self, self._tool[1])

        except IndexError:
            print(' !! index out of range')


    def print_rooms(self, *_):
        if not self.rooms:
            self.get_rooms()

        for idx, room in enumerate(self.rooms):
            print('[%i] %s' % (idx, room[0]))
        

    def print_tools(self, *_):
        if not self.tools:
            self.scrape_room()

        for idx, tool in enumerate(self.tools):
            print('[%i] %s' % (idx, tool[0]))


def loop(cli):

    cli.print_actions()

    while True:
        try:
            action = raw_input('> ').strip()
            if not action:
                continue
            arg = None
            if action.startswith('select'):
                action, arg = action.split()
                arg = int(arg)
            cli = cli.actions[action](arg) or cli
        except KeyError:
            print(' !! invalid action')
            print_actions()
        except ValueError, TypeError:
            print(' !! integer argument required')
        except EOFError:
            print('')
            continue


if __name__ == '__main__':
    cli = Fronter()
    try:
        cli.login()
        loop(cli)
    except ValueError:
        print('Wrong username/password')
        sys.exit(0)




