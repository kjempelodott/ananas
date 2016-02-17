try: # Because python shell in OS X is stupid and doesn't exit upon ImportError
    from lxml.html import fromstring, tostring
except ImportError as err:
    print(err)
    exit()

import os, sys, re, stat, base64
from datetime import datetime
from tempfile import mkstemp
from shutil import copyfileobj, copy
from collections import OrderedDict, namedtuple
from subprocess import call
from email.generator import _make_boundary as choose_boundary
import mimetypes

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


def wrap(text):
    from textwrap import fill
    return '\n'.join(fill(line, replace_whitespace=False) for line in text.splitlines())


class Editor():

    def __init__(self):
        self.editor = os.getenv('VISUAL') or os.getenv('EDITOR') or \
                      ('nano', 'notepad.exe')[sys.platform[:3] == 'win']
        self.editor = self.editor.split()

    def edit(self, fname):
        mtime = os.stat(fname).st_mtime
        call(self.editor + [fname])
        return mtime != os.stat(fname).st_mtime

    def new(self):
        fd, fname = mkstemp(prefix='fronter_')
        self.edit(fname)
        return fd, fname


# TODO: No need for a class
class Color():

    def __init__(self):

        self.HEAD = '\033[1;33m'
        self.HL   = '\033[1;36m'
        self.DIR  = '\033[1;34m'
        self.ERR  = '\033[31m'
        self.END  = '\033[0m'

    def colored(self, text, style = '\033[m', padding = False):
        return style + text + self.END + padding * ' ' * (8 - len(style))


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
        self.TARGET   = client.TARGET
        self.ROOT     = client.ROOT

        self.opener   = client.opener

        self.get_form = client.get_form
        self.get      = client.get
        self.get_xml  = client.get_xml
        self.post     = client.post

        self._request = client._request
        self._request.func_globals['CLASS'] = self.__class__.__name__

    def print_commands(self):
        print(col('%s commands:' % str(self), c.HEAD))
        print(col('return <Ctrl-D>', c.HL))
        print('\n'.join(str(a) for a in self.commands.values()))

    def clean_exit(self):
        pass

    @staticmethod
    def _ask(question):
        yn = ''
        while yn not in ('y', 'n'):
            yn = input('> %s (y/n) ' % question).strip()
        return yn == 'y'


import html
from .survey import Survey
from .members import Members
from .filetree import FileTree
from .roominfo import RoomInfo
