import os, sys, re
from datetime import datetime
from collections import OrderedDict
from shutil import copyfileobj
from lxml import html

from main import Fronter

if sys.version_info[0] == 2:
    input = raw_input


class Tool(object):

    class Action:

        def __init__(self, cmd, function, argstr, desc):
            self.cmd = cmd
            self.function = function
            self.argstr = argstr
            self.desc = desc

        def __call__(self, *arg):
            self.function(*arg)

        def __str__(self):
            return '%-20s %s' % (('%-4s %s') % (self.cmd, self.argstr), self.desc)

    def __init__(self):
        self.actions = OrderedDict()
        self.actions['h'] = Tool.Action('h', self.print_actions, '', 'print actions')

    def __str__(self):
        return self.__class__.__name__

    def print_actions(self):
        print('%s actions:' % str(self))
        print('return <Ctrl-D>')
        print('\n'.join(str(a) for a in self.actions.values()))


class Deltakere(Tool):

    class Member:

        def __init__(self, name, email, label):
            self.name = name
            self.email = email
            self.label = label.lower()

        def __str__(self):
            return '%-40s %-40s %s' % (self.name, self.email, self.label)


    def __init__(self, client, url):

        super(Deltakere, self).__init__()
        self.opener = client.opener
        self.members = []
        self.get_members(url)

        self.actions['pm'] = Tool.Action('pm', self.print_members, '', 'print members')
        self.actions['mt'] = \
            Tool.Action('mt', self.mailto, '<index/label>', 'send mail to a (group of) member(s)')


    def get_members(self, url):

        response = self.opener.open(url)
        tree = html.fromstring(response.read())
        name = tree.xpath('//tr/td[2]/label/a[@class="black-link"]')
        email = tree.xpath('//tr/td[4]/label/a[@class="black-link"]')
        label = tree.xpath('//tr/td[last()]/label')
        for n, e, a in zip(name, email, label):
            self.members.append(Deltakere.Member(n.text, e.text, a.text))


    def print_members(self):

        for idx, member in enumerate(self.members):
            print('[%-3i] %s' % (idx, memeber))


    def mailto(self, select):

        who = None
        try:
            who = [self.members[int(select)]]
        except ValueError:
            who = [member for member in self.members if member.label == select]
            if not who:
                raise ValueError

        for member in who:
            print(' * %s' % member.name)

        print('> write a message (end with Ctrl-D):')
        print('"""')
        message = ''
        while True:
            try:
                message += input('') + '\n'
            except EOFError:
                break
        print('"""')

        yn = ''
        while yn not in ('y', 'n'):
            yn = input('> send this message? (y/n) ')
        if yn == 'y':
            print(' ... sending ... ')


class Rapportinnlevering(Tool):

    class Delivery:

        def __init__(self, firstname, lastname, fileurl, date):
            self.firstname = firstname
            self.lastname = lastname
            self.fileurl = fileurl
            self.date = date.strftime('%Y-%m-%d') if date else None

        def __str__(self):
            return '%-15s %s, %s' % (self.date, self.lastname, self.firstname)


    def __init__(self, client, url):

        super(Rapportinnlevering, self).__init__()
        self.opener = client.opener
        self.assignments = []
        self.get_assignments(url)

        self.actions['pa'] = Tool.Action('pa', self.print_assignments, '', 'print assignments')
        self.actions['sa'] = Tool.Action('sa', self.select_assignment, '<index>', 'select an assignment')
        self.actions['pd'] = Tool.Action('pd', self.print_deliveries, '', 'print deliveries')
        self.actions['da'] = Tool.Action('da', self.download_all, '', 'download all deliveries')
        self.actions['d']  = Tool.Action('d', self.download, '<index>', 'download a delivery')
        

    def get_assignments(self, url):

        response = self.opener.open(url)
        treeid = re.findall('root_node_id=([0-9]+)', response.read().decode('utf-8'))[0]
        url = Fronter.TARGET + '/links/structureprops.phtml?treeid=' + treeid

        response = self.opener.open(url)
        tree = html.fromstring(response.read())
        assignments = tree.xpath('//a[@class="black-link"]')
        for assignment in assignments:
            self.assignments.append((assignment.text, 'links/' + assignment.get('href')))
        
    def print_assignments(self):

        for idx, assignment in enumerate(self.assignments):
            print('[%-3i] %s' % (idx, assignment[0]))


    def select_assignment(self, idx):

        self.deliveries = []
        response = self.opener.open(Fronter.TARGET + self.assignments[int(idx)][1])
        tree = html.fromstring(response.read())

        name = tree.xpath('//tr/td[2]/label')
        url = tree.xpath('//tr/td[3]')
        status = tree.xpath('//tr/td[4]/label')

        for n, a, s in zip(name, url, status):

            first = n.text.strip()
            last = n.getchildren()[0].text.strip()

            date = None
            try:
                date = datetime.strptime(s.text.strip(),'%Y-%m-%d')
                a = a.xpath('a[@class=""]')[0].get('href').strip()
            except ValueError:
                a = None

            self.deliveries.append( Rapportinnlevering.Delivery(first, last, a, date) )


    def print_deliveries(self):

        try:
            for idx, delivery in enumerate(self.deliveries):
                print('[%-3i] %s' % (idx, delivery))
                  
        except AttributeError:
            print(' !! you must select an assignment first')


    def download(self, idx, folder = None):

        d = self.deliveries[int(idx)]

        if not folder:
            folder = self.get_folder()
            
        fileurl = d.fileurl
        if not fileurl:
            return

        basename = os.path.basename(fileurl)
        fname = os.path.join(folder, '%s_%s' % (d.lastname, basename))
        with open(fname, 'wb') as local:
            copyfileobj(self.opener.open(Fronter.ROOT + fileurl), local)
        print(' * %s' % fname)


    def download_all(self):
        
        folder = self.get_folder()
        for idx in range(len(self.deliveries)):
            self.download(idx, folder)


    def get_folder(self):

        folder = os.getcwd()
        userinput = input('> select folder (%s) : ' % folder)
        folder = userinput if userinput else folder
        
        try:
            try:
                os.mkdir(folder)
            except OSError as oe:
                assert(oe.errno == 17)
            assert(os.access(folder, os.W_OK))
        except AssertionError:
            print(' !! failed to create dir')
            raise EOFError

        return folder
