#!/usr/bin/env python

import re, sys
from collections import OrderedDict
from urllib2 import HTTPCookieProcessor, HTTPRedirectHandler, build_opener
from urllib import urlencode
from getpass import getuser, getpass
from lxml import html

from tools import *


class Fronter(object):

    class Room(object):

        def __init__(self, name, roomid):
            self.name = name
            self.id = roomid
            self.tools = []


    TARGET = 'https://fronter.com/uio/'

    _imp = ('Deltakere', 'Rapportinnlevering')

    def __init__(self):

        self.cookie_jar = HTTPCookieProcessor()
        self.opener = build_opener(HTTPRedirectHandler, self.cookie_jar)
        self.rooms = {}
        self.login()

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
        self.rooms = [ Fronter.Room( room.text.strip(), int(room.get('href').split('=')[-1]) )
                       for room in rooms ]


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
            url = Fronter.TARGET + '/contentframeset.phtml?goto_prjid=%i' % room.id
            self.opener.open(url)
            # Read the 'toolbar' on the right hand side
            url = Fronter.TARGET + '/navbar.phtml?goto_prjid=%i' % room.id
            response = self.opener.open(url)
            tree = html.fromstring(response.read())
            tools = tree.xpath('//a[@class="room-tool"]')

            for tool in tools:
                title = tool.xpath('span[@class="tool-title"]')[0].text
                if title in Fronter._imp:
                    room.tools.append( [ title, tool.get('href') ] )

        except AttributeError:
            print(' !! you must select a room first')
        

    def select_tool(self, idx):

        tool = self.rooms[self.roomid].tools[idx]
        print(' * %s' % tool[0])
        if type(tool[1]) is str:
            tool[1] = globals()[tool[0]](self, Fronter.TARGET + tool[1])
        return tool[1]


    def print_rooms(self):

        print('exit   <Ctrl-C>')
        print('return <Ctrl-D>')
        for idx, room in enumerate(self.rooms):
            print('[%-3i] %s' % (idx, room.name))

    def print_tools(self):

        print('exit   <Ctrl-C>')
        print('return <Ctrl-D>')
        for idx, tool in enumerate(self.rooms[self.roomid].tools):
            print('[%-3i] %s' % (idx, tool[0]))


def loop(tool):

    if not tool:
        return
    tool.print_actions()

    while True:
        try:
            action = raw_input('> ').strip()
            if not action:
                continue
            arg = []
            try:
                action, arg = action.split()
                arg = [arg]
            except:
                pass
            tool.actions[action](*arg)
        except KeyError:
            print(' !! invalid action')
            tool.print_actions()
        except IndexError:
            print(' !! index out of range')
        except (ValueError, TypeError):
            print(' !! invalid argument')
        except EOFError:
            print('')
            break
        except KeyboardInterrupt:
            print('')


client = None

def main():

    try:
        global client
        client = Fronter()
    except ValueError:
        print('Wrong username/password')
        sys.exit(0)
    except (KeyboardInterrupt, EOFError):
        print('\n> exit')
        sys.exit(0)
        
    client.get_rooms() 

    while True:        
        try:
            print('')
            client.print_rooms()

            idx = int(raw_input('> select a room <index> : ').strip())
            client.select_room(idx)

            while True:

                print('')
                client.print_tools()

                try:
                    idx = int(raw_input('> select a tool <index> : ').strip())
                    tool = client.select_tool(idx)
                    print('')
                    loop(tool)
                except ValueError:
                    print(' !! integer argument required')
                except IndexError:
                    print(' !! index out of range')
                except EOFError:
                    print('')
                    break

        except ValueError:
            print(' !! integer argument required')
        except IndexError:
            print(' !! index out of range')
        except (KeyboardInterrupt, EOFError):
            print('\n> exit')
            break


if __name__ == '__main__':
    main()
