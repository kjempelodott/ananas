import re
from collections import OrderedDict
from lxml import html

from main import Fronter

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
        print('\n'.join(str(a) for a in self.actions.itervalues()))


class Deltakere(Tool):

    class Member:

        def __init__(self, name, email, label):
            self.name = name
            self.email = email
            self.label = label.lower()


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
            print('[%-3i] %-40s %-40s %s' % (idx, member.name, member.email, member.label))


    def mailto(self, select):

        who = None
        try:
            who = [self.members[int(select)]]
        except ValueError:
            print select
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
                message += raw_input('') + '\n'
            except EOFError:
                break
        print('"""')

        yn = ''
        while yn not in ('y', 'n'):
            yn = raw_input('> send this message? (y/n) ')
        if yn == 'y':
            print(' ... sending ... ')


class Rapportinnlevering(Tool):

    class Delivery:

        def __init__(self, name, fileurl, status, filesize):
            self.name = name
            self.fileurl = fileurl
            self.status = status
            self.filesize = filesize

    def __init__(self, client, url):

        super(Rapportinnlevering, self).__init__()
        self.opener = client.opener
        self.assignments = []
        self.get_assignments(url)

        self.actions['pa']  = Tool.Action('pa', self.print_assignments, '', 'print assignments')
        self.actions['sa'] = Tool.Action('sa', self.select_assignment, '<index>', 'select an assignment')
        self.actions['pd']  = Tool.Action('pd', self.print_deliveries, '', 'print deliveries')
        self.actions['da'] = Tool.Action('da', self.download_all, '', 'download all deliveries')
        self.actions['di'] = Tool.Action('d', self.download, '<index>', 'download a delivery')
        

    def get_assignments(self, url):

        response = self.opener.open(url)
        treeid = re.findall('root_node_id=([0-9]+)', response.read())[0]
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
        fileurl = tree.xpath('//tr/td[3]/a[@class="black-link"]')
        status = tree.xpath('//tr/td[4]/label')
        filesize = tree.xpath('//tr/td[6]/label')
        for n, fu, s, fs in zip(name, fileurl, status, filesize):
            self.deliveries.append(Delivery(n.text, fu.get('href', s.text, fs.text)))

    def print_deliveries(self):

        try:
            for idx, delivery in enumerate(self.deliveries):
                print('[%-3i] %-20s %s' % (idx, delivery.status, delivery.name))
                  
        except AttributeError:
            print(' !! you must select an assignment first')


    def download(self, idx):
        pass

    def download_all(self):
        pass
