import os, sys, re, stat, base64
from datetime import datetime
from tempfile import mkstemp
from shutil import copyfileobj, copy
from collections import OrderedDict, namedtuple
from lxml import html, etree

if sys.version_info[0] == 2:
    from ConfigParser import ConfigParser
    from urllib import urlencode, unquote_plus
    from urllib2 import BaseHandler, HTTPHandler, HTTPRedirectHandler, \
        build_opener, HTTPCookieProcessor, HTTPError
    from HTMLParser import HTMLParser
    input = raw_input
else:
    from configparser import ConfigParser
    from urllib.request import BaseHandler, HTTPHandler, HTTPRedirectHandler, \
        HTTPCookieProcessor, build_opener
    from urllib.parse import urlencode, unquote_plus
    from urllib.error import HTTPError
    from html.parser import HTMLParser

from .plugins import Color, Editor

c = Color()
col = c.colored
txt = Editor()


class NewToolInterrupt(BaseException):

    def __init__(self, tool):
        self.tool = tool


class Tool(object):

    class Command:

        def __init__(self, cmd, function, argstr, desc):
            self.cmd      = cmd
            self.function = function
            self.argstr   = argstr
            self.desc     = desc

        def __call__(self, *arg):
            self.function(*arg)

        def __str__(self):
            return '%-24s %s' % (('%-8s %s') % (self.cmd, self.argstr), self.desc)

    def __init__(self):

        self.commands = OrderedDict()
        self.commands['exit'] = Tool.Command('exit', sys.exit, '', 'exit')
        self.commands['h']    = Tool.Command('h', self.print_commands, '', 'print commands')

    def __str__(self):
        return self.__class__.__name__

    @property
    def client(self): pass

    @client.setter
    def client(self, client):
        self.TARGET = client.TARGET
        self.ROOT   = client.ROOT
        self.opener = client.opener

    def print_commands(self):
        print(col('%s commands:' % str(self), c.HEAD))
        print(col('return <Ctrl-D>', c.HL))
        print('\n'.join(str(a) for a in self.commands.values()))

    def prepare_form(self, xml):

        form = xml.xpath('//form[@name="actionform"]')[0]
        inputs = form.xpath('input[@type="hidden"]')
        payload = dict((i.name, i.get('value')) for i in inputs)

        url = form.get('action').lstrip('..')
        return url, payload

    def clean_exit(self):
        pass

    @staticmethod
    def _ask(question):
        yn = ''
        while yn not in ('y', 'n'):
            yn = input('> %s (y/n) ' % question).strip()
        return yn == 'y'


from .survey import Survey
from .members import Members
from .filetree import FileTree
from .roominfo import RoomInfo
