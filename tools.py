import os, sys, re
from datetime import datetime
from collections import OrderedDict
from shutil import copyfileobj
from lxml import html
from plugins import Mailserver

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



class Members(Tool):

    class Member:

        def __init__(self, name, email, label):
            self.name = name
            self.email = email
            self.label = label.lower()

        def __str__(self):
            return self.__unicode__()

        def __unicode__(self):
            return '%-40s %-40s %s' % (self.name, self.email, self.label)


    def __init__(self, client, url):

        super(Members, self).__init__()
        self.mailserver = Mailserver(client.__user__, client.__secret__)
        self.opener = client.opener
        self.members = []
        self.get_members(url)

        self.actions['p']  = Tool.Action('p', self.print_members, '', 'print members')
        self.actions['mt'] = \
            Tool.Action('mt', self.mailto, '<index/label>', 'send mail to a (group of) member(s)')


    def get_members(self, url):

        response = self.opener.open(url)
        xml = html.fromstring(response.read())
        name = xml.xpath('//tr/td[2]/label/a[@class="black-link"]')
        email = xml.xpath('//tr/td[4]/label/a[@class="black-link"]')
        label = xml.xpath('//tr/td[last()]/label')
        for n, e, a in zip(name, email, label):
            self.members.append(Members.Member(n.text, e.text, a.text))


    def print_members(self):

        for idx, member in enumerate(self.members):
            print('[%-3i] %s' % (idx, member))


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

        self.mailserver.sendmail(who)



class FileTree(Tool):

    class Branch(object):

        def __init__(self, title, treeid, parent):
            self.title = title
            self.treeid = treeid
            self.parent = parent

        def __str__(self):
            return self.__unicode__()

        def __unicode__(self):
            return '[ %s ]' % (self.title)


    class Leaf(object):

        def __init__(self, title, url, parent):
            self.title = title
            self.url = url
            self.parent = parent

        def __str__(self):
            return self.__unicode__()

        def __unicode__(self):
            return '%s' % (self.title)


    class Delivery(object):

        def __init__(self, firstname, lastname, url, date, parent):
            self.firstname = firstname
            self.lastname = lastname
            self.url = url
            self.date = date.strftime('%Y-%m-%d') if date else None
            self.parent = parent

        def __str__(self):
            return self.__unicode__()

        def __unicode__(self):
            return '%-15s %s, %s' % (self.date, self.lastname, self.firstname)


    def __init__(self, client, url):

        super(FileTree, self).__init__()
        self.opener = client.opener
        self.init_tree(url)

        self.actions['p'] = Tool.Action('p', self.print_content, '', 'print content of current dir')
        self.actions['gt'] = Tool.Action('gt', self.goto_idx, '<index>', 'goto dir (up: -1)')
        self.actions['da'] = Tool.Action('da', self.download_all, '', 'download all files')
        self.actions['d']  = Tool.Action('d', self.download, '<index>', 'download a file')
        

    def init_tree(self, url):

        self.__trees__ = {}
        response = self.opener.open(url)
        treeid = re.findall('root_node_id=([0-9]+)', response.read().decode('utf-8'))[0]
        self.goto_branch(int(treeid))
    

    def goto_branch(self, parent, treeid = None):

        treeid = treeid if treeid else parent
        if treeid in self.__trees__:
            self._current = self.__trees__[treeid]
            return

        url = Fronter.TARGET + '/links/structureprops.phtml?treeid=%i' % treeid
        response = self.opener.open(url)
        xml = html.fromstring(response.read())
        delivery_folder = bool(xml.xpath('//td/label[@for="folder_todate"]'))
 
        branches = []
        leafs = []

        if delivery_folder:

            name = xml.xpath('//tr/td[2]/label')
            url = xml.xpath('//tr/td[3]')
            status = xml.xpath('//tr/td[4]/label')

            for n, a, s in zip(name, url, status):

                first = n.text.strip()
                last = n.getchildren()[0].text.strip()

                date = None
                try:
                    date = datetime.strptime(s.text.strip(),'%Y-%m-%d')
                    a = a.xpath('a[@class=""]')[0].get('href').strip()
                except ValueError:
                    a = None

                leafs.append(FileTree.Delivery(first, last, a, date, parent))

        else:

            items = xml.xpath('//a[@class="black-link"]')
            for item in items:
                href = item.get('href')
                try:
                    tid = int(re.findall('treeid=([0-9]+)', href)[0])
                    branches.append(FileTree.Branch(item.text, tid, parent))
                except:
                    leafs.append(FileTree.Leaf(item.text, href, parent))           

        if not branches and not leafs:
            print(' !! empty dir')
        else:
            self._current = self.__trees__[treeid] = { 'branches' : branches, 'leafs': leafs }


    def print_content(self):

        tree = self._current
        for items in (tree['branches'], tree['leafs']):
            for idx, item in enumerate(items):
                print('[%-3i] %s' % (idx, item))


    def goto_idx(self, idx):

        idx = int(idx)

        if idx == -1:
            children = self._current['branches'] + self._current['leafs']
            if children:
                self.goto_branch(children[-1].parent)
            # Else - an empty FileTree
            return

        branches = self._current['branches']
        if idx >= len(branches):
            print(' !! not a dir')
            return
        
        branch = branches[idx]
        self.goto_branch(branch.parent, branch.treeid)


    def download(self, idx, folder = None):

        f = self._current['leafs'][int(idx)]

        if not f.url: # Deliveries may have no url
            return

        if not folder:
            folder = self.get_local_folder()

        fname = os.path.basename(f.url)
        if type(f) is FileTree.Delivery:
            fname = '%s_%s' % (f.lastname, fname)
        fname = os.path.join(folder, fname)

        with open(fname, 'wb') as local:
            copyfileobj(self.opener.open(Fronter.ROOT + f.url), local)
        print(' * %s' % fname)


    def download_all(self):
        
        nfiles = len(self._current['leafs'])
        if not nfiles:
            print(' !! no files in current dir')
            return
            
        folder = self.get_local_folder()
        for idx in range(nfiles):
            self.download(idx, folder)


    def get_local_folder(self):

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
