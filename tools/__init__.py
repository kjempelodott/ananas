import os, sys, re
from datetime import datetime
from collections import OrderedDict
from lxml import html, etree
from plugins import Color, Editor

if sys.version_info[0] == 2:
    from urllib import urlencode, unquote_plus
    from HTMLParser import HTMLParser
    input = raw_input
else:
    from urllib.parse import urlencode, unquote_plus
    from html.parser import HTMLParser


c = Color()
col = c.colored
txt = Editor()


class Tool(object):

    class Command:

        def __init__(self, cmd, function, argstr, desc):
            self.cmd = cmd
            self.function = function
            self.argstr = argstr
            self.desc = desc

        def __call__(self, *arg):
            self.function(*arg)

        def __str__(self):
            return '%-24s %s' % (('%-8s %s') % (self.cmd, self.argstr), self.desc)

    def __init__(self):

        self.commands = OrderedDict()
        self.commands['exit'] = Tool.Command('exit', sys.exit, '', 'exit')
        self.commands['h'] = Tool.Command('h', self.print_commands, '', 'print commands')

    def __str__(self):
        return self.__class__.__name__

    def print_commands(self):
        print(col('%s commands:' % str(self), c.HEAD))
        print(col('return <Ctrl-D>', c.HL))
        print('\n'.join(str(a) for a in self.commands.values()))

    def prepare_form(self, xml):

        form = xml.xpath('//form[@name="actionform"]')[0]
        inputs = form.xpath('input[@type="hidden"]')
        payload = dict((i.name, i.get('value')) for i in inputs)

        url = form.get('action')
        if not url.startswith(self.TARGET):
            url = url.lstrip('..')

        return url, payload
