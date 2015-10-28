import os, sys, re
from datetime import datetime
from collections import namedtuple, OrderedDict
from shutil import copyfileobj
from lxml import html
from plugins import Mailserver

from pyshell import Fronter

if sys.version_info[0] == 2:
    from urllib import urlencode
    input = raw_input
else:
    from urllib.parse import urlencode


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
            return '%-20s %s' % (('%-4s %s') % (self.cmd, self.argstr), self.desc)

    def __init__(self):
        self.commands = OrderedDict()
        self.commands['h'] = Tool.Command('h', self.print_commands, '', 'print commands')

    def __str__(self):
        return self.__class__.__name__

    def print_commands(self):
        print('%s commands:' % str(self))
        print('return <Ctrl-D>')
        print('\n'.join(str(a) for a in self.commands.values()))



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

        self.commands['ls']  = Tool.Command('ls', self.print_members, '', 'list members')
        self.commands['mail'] = \
            Tool.Command('mail', self.mailto, '<index/label>', 'send mail to a (group of) member(s)')


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

        _imp = ('multi_delete', 'new_comment')
        Menu = namedtuple('Menu', ['name', 'url'])

        def __init__(self, title, treeid, parent):
            self.title = title
            self.treeid = treeid
            self.parent = parent
            self.menu = {}

        def __str__(self):
            return self.__unicode__()

        def __unicode__(self):
            return '[ %s ]' % (self.title)

        def make_menu(self, menu = {}):
            for item in menu.split(','):
                try:
                    key, url = item.split('^')
                    action = url.split('action=')[1].split('&')[0]
                    assert(action in FileTree.Branch._imp)
                    self.menu[action] = FileTree.Branch.Menu(name = key.strip('"'), url = url)
                except (AssertionError, IndexError):
                    continue


    class Leaf(Branch):

        def __init__(self, title, url, parent):
            self.title = title
            self.url = url
            self.parent = parent
            self.menu = {}

        def __unicode__(self):
            return '  %s' % (self.title)


    class Delivery(Leaf):

        def __init__(self, firstname, lastname, url, date, parent):
            self.firstname = firstname
            self.lastname = lastname
            self.title = '%s %s' % (firstname, lastname)
            self.url = url
            self.date = date.strftime('%Y-%m-%d') if date else None
            self.parent = parent
            self.menu = {}

        def __unicode__(self):
            return '%-15s %s, %s' % (self.date, self.lastname, self.firstname)
                

    def __init__(self, client, url):

        super(FileTree, self).__init__()
        self.opener = client.opener
        self.init_tree(url)

        self.commands['ls'] = Tool.Command('ls', self.print_content, '', 'list content of current dir')
        self.commands['cd'] = Tool.Command('cd', self.goto_idx, '<index/..>', 'change dir')

        self.commands['get#'] = Tool.Command('get#', self.download_all, '', 
                                             'download all files in current dir')
        self.commands['get']  = Tool.Command('get', self.download, '<index>', 'download a file')

        self.commands['del#'] = Tool.Command('del#', self.delete_all, '', 'delete all in current dir')
        self.commands['del']  = Tool.Command('del', self.delete, '<index>', 'delete a file/dir')

        self.commands['comment#'] = Tool.Command('comment#', self.comment_all, '', 
                                                 'upload comments from xml')
        self.commands['comment']  = Tool.Command('comment', self.comment, '<index>', 'upload comment')
        

    def init_tree(self, url):

        self.__trees__ = {}
        response = self.opener.open(url)
        self._current = int(re.findall('root_node_id=([0-9]+)', response.read().decode('utf-8'))[0])
        self.goto_branch(self._current)
    

    def goto_branch(self, treeid):

        if treeid in self.__trees__:
            self._current = treeid
            return

        url = Fronter.TARGET + '/links/structureprops.phtml?treeid=%i' % treeid
        response = self.opener.open(url)
        data = response.read().decode('utf-8')
        xml = html.fromstring(data)
        delivery_folder = bool(xml.xpath('//td/label[@for="folder_todate"]'))
 
        branches = []
        leafs = []

        menus = dict((mid, menu) for mid, menu in
                     re.findall('ez_Menu\[\'([0-9]+)\'\][=_\s\w]+\(\"(.+)"\)', data))

        if delivery_folder:

            tr_odd = xml.xpath('//tr[@class=tablelist-odd]')
            tr_even = xml.xpath('//tr[@class=tablelist-even]')
            
            for tr in tr_odd + tr_even:
                try:
                    name = tr.xpath('td[2]/label')[0]
                    url = tr.xpath('td[3]')[0]
                    status = tr.xpath('td[4]/label')[0]

                    first = name.text.strip()
                    last = name.getchildren()[0].text.strip()

                    date, menu = None, {}
                    try:
                        date = datetime.strptime(status.text.strip(),'%Y-%m-%d')
                        url = url.xpath('a[@class=""]')[0].get('href').strip()
                        menu_id = url.xpath('a[@class="ez-menu"]')[0].get('name')
                        menu = menus[menu_id]
                    except ValueError:
                        url = None
                        
                    leafs.append(FileTree.Delivery(first, last, url, date, self._current))
                    leafs[-1].make_menu(menu)

                except IndexError:
                    continue

        else:

            links = xml.xpath('//a[@class="black-link"]')
            menu_ids = xml.xpath('//a[@class="ez-menu"]')

            for link, menu_id in zip(links, menu_ids):
                href = link.get('href')
                menu_id = menu_id.get('name')
                menu = menus[menu_id]
                try:
                    tid = int(re.findall('treeid=([0-9]+)', href)[0])
                    branches.append(FileTree.Branch(link.text, tid, self._current))
                    branches[-1].make_menu(menu)
                except:
                    leafs.append(FileTree.Leaf(link.text, href, self._current))
                    leafs[-1].make_menu(menu)


        if not branches and not leafs:
            print(' !! empty dir')
        else:
            self.__trees__[treeid] = { 'branches' : branches, 'leafs': leafs }
            self._current = treeid


    def print_content(self):

        tree = self.__trees__[self._current]
        for items in (tree['branches'], tree['leafs']):
            for idx, item in enumerate(items):
                print('[%-3i] %s' % (idx, item))


    def goto_idx(self, idx):

        tree = self.__trees__[self._current]
        if idx == '..':
            children = tree['branches'] + tree['leafs']
            if children:
                self.goto_branch(children[-1].parent)
            # Else - an empty FileTree
            return

        idx = int(idx)
        branches = tree['branches']
        if idx >= len(branches):
            print(' !! not a dir')
            return
        
        branch = branches[idx]
        self.goto_branch(branch.treeid)


    def download(self, idx, folder = None):

        f = self.__trees__[self._current]['leafs'][int(idx)]

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
        
        nfiles = len(self.__trees__[self._current]['leafs'])
        if not nfiles:
            print(' !! no files in current dir')
            return
            
        folder = self.get_local_folder()
        for idx in range(nfiles):
            self.download(idx, folder)

    
    def delete(self):
        print('not implemented yet')
        return


    def delete_all(self):
        print('not implemented yet')
        return


    def comment(self, idx, comment = '', grade = '', evaluation = '', autoyes = False):

        f = self.__trees__[self._current]['leafs'][int(idx)]
        if not 'new_comment' in f.menu:
            print(' !! commenting not available (%s)' % f.title)
            return

        response = self.opener.open(Fronter.TARGET + '/links/' + f.menu['new_comment'].url)
        xml = html.fromstring(response.read())
        evals = [(item.getnext().text, item.get('value'))
                 for item in xml.xpath('//input[@type="radio"]')]

        if not evaluation:
            print('')
            for idx, evali in enumerate(evals):
                print('[%-3i] %s' % (idx, evali[0]))
            evaluation = evals[int(input('> evaluation <index> : ').strip())][1]

        if not grade:
            grade = input('> grade : ')

        if not comment:
            print('> comment (end with Ctrl-D):')
            print('"""')
            while True:
                try:
                    comment += input('') + '\n'
                except EOFError:
                    break
            print('"""')
            
        yn = '' if not autoyes else 'y'
        while yn not in ('y', 'n'):
            yn = input('> upload evaluation, grade and comment? (y/n) ')

        if yn == 'y':
            form = xml.xpath('//form[@name="actionform"]')[0]
            inputs = form.xpath('input[@type="hidden"]')
            payload = dict((i.name, i.get('value')) for i in inputs)
 
            payload['submit_clicked']  = 1
            payload['do_action']       = 'comment_save'
            payload['element_comment'] = comment
            payload['grade']           = grade
            payload['aproved']         = evaluation

            url = form.get('action')
            self.opener.open(url, urlencode(payload).encode('ascii'))


    def comment_all(self):
        print('not implemented yet')
        return
        userinput = input('> input comments file : ')
        try:
            with open(userinput, 'r') as f:
                content = XMLParser(f.read())

 #          for 

 #             print(name)   
 #             print(comment[0:20], '...')
 #             print('grade:', grade)

 #          input(ok? y/n)

            
        except OSError as oe:
            if (oe.errno == 2):
                print(' !! %s does not exist' % userinput)
            else:
                print(' !! failed to read %s' % userinput)
            raise EOFError


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
