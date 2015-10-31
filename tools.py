import os, sys, re
from datetime import datetime
from collections import namedtuple, OrderedDict
from shutil import copyfileobj
from lxml import html
from plugins import Mailserver, Color

if sys.version_info[0] == 2:
    from urllib import urlencode
    input = raw_input
else:
    from urllib.parse import urlencode

c = Color()
col = c.colored


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


class Members(Tool):

    class Member:

        def __init__(self, name, email, label):

            self.name = name
            self.email = email
            self.label = label.lower()

        # __str__ is broken in Python 2 - tries to encode in ascii
        def str(self):
            return '%-35s %-45s %s' % (self.name, 
                                       col(self.email, c.HL), 
                                       col(self.label, c.HEAD))

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
            print(col('[%-3i] ' % idx, c.HL) + member.str())


    def mailto(self, select):

        who = None
        try:
            who = [self.members[int(select)]]
        except ValueError:
            if select[0] == '!':
                who = [member for member in self.members if member.label != select[1:]]
            else:
                who = [member for member in self.members if member.label == select]
            if not who:
                raise ValueError

        for member in who:
            print(col(' * ', c.ERR) + member.name)

        self.mailserver.sendmail(who)


class FileTree(Tool):

    class Branch(object):

        _imp = ('multi_delete', 'new_comment')
        Menu = namedtuple('Menu', ['name', 'url'])

        def __init__(self, title, treeid, parent = None):

            self.title = title
            self.treeid = treeid
            self.parent = parent
            self.path = '/' if not parent else parent.path + title + '/'
            self.children = { 'leafs' : [], 'branches' : [] }
            self.menu = {}

        def str(self):
            return col(self.title, c.DIR)

        def make_menu(self, menu = ''):
            for item in menu.split(','):
                try:
                    key, url = item.split('^') # ValueError
                    action = url.split('action=')[1].split('&')[0] # IndexError
                    assert(action in FileTree.Branch._imp)
                    self.menu[action] = FileTree.Branch.Menu(name = key.strip('"'), url = url)
                except (AssertionError, ValueError, IndexError):
                    continue


    class Leaf(Branch):

        def __init__(self, title, url, parent):

            self.title = title
            self.url = url
            self.parent = parent
            self.menu = {}

        def str(self):
            return self.title


    class Delivery(Leaf):

        def __init__(self, firstname, lastname, url, date, parent):

            self.firstname = firstname
            self.lastname = lastname
            self.title = '%s %s' % (firstname, lastname)
            self.url = url
            self.date = col(date.strftime('%Y-%m-%d'), c.HL, True) if date else col('NA', c.ERR, True)
            self.parent = parent
            self.menu = {}

        def str(self):
            return '%-20s %s' % (self.date, self.title)
                

    def __init__(self, client, url):

        self.TARGET = client.TARGET
        self.ROOT = client.ROOT
        self.url = url

        super(FileTree, self).__init__()
        self.opener = client.opener

        self.init_tree()
    
        # Shell-like filesystem stuff
        self.commands['ls'] = Tool.Command('ls', self.print_content, '', 'list content of current dir')
        self.commands['cd'] = Tool.Command('cd', self.goto_idx, '<index/..>', 'change dir')
        # Download
        self.commands['get#'] = Tool.Command('get#', self.download_all, '', 
                                             'download all files in current dir')
        self.commands['get']  = Tool.Command('get', self.download, '<index>', 'download a file')
        # Upload
        self.commands['put'] = Tool.Command('put', self.upload, '', 'upload file(s) to current dir')
        # Delete
        self.commands['del#'] = Tool.Command('del#', self.delete_all, '', 'delete all in current dir')
        self.commands['del']  = Tool.Command('del', self.delete, '<index>', 'delete a file/dir')
        # Evaluate
        self.commands['eval#'] = Tool.Command('eval#', self.evaluate_all, '', 
                                              'upload evaluations from xml')
        self.commands['eval']  = Tool.Command('eval', self.evaluation, '<index>', 
                                              'read and edit evaluation')
        # Reload
        self.commands['reload']  = Tool.Command('reload', self.init_tree, '', 'reload (clean cache)')

        
    def init_tree(self):
        
        response = self.opener.open(self.url)
        treeid = int(re.findall('root_node_id=([0-9]+)', response.read().decode('utf-8'))[0])
        root = FileTree.Branch('', treeid)
        self.__trees__ = {} # Keeps all branches in memory
        self.goto_branch(root)
    

    def goto_branch(self, branch):

        treeid = branch.treeid
        if treeid in self.__trees__:
            self.cwd = branch
            return

        url = self.TARGET + '/links/structureprops.phtml?treeid=%i' % treeid
        response = self.opener.open(url)
        data = response.read()
        xml = html.fromstring(data)
        branch.is_task = bool(xml.xpath('//td/label[@for="folder_todate"]'))

        branches = []
        leafs = []

        menus = dict((mid, menu) for mid, menu in
                     re.findall('ez_Menu\[\'([0-9]+)\'\][=_\s\w]+\(\"(.+)"\)', 
                                data.decode('utf-8')))

        if branch.is_task:

            tr_odd = xml.xpath('//tr[@class="tablelist-odd"]')
            tr_even = xml.xpath('//tr[@class="tablelist-even"]')

            for tr in tr_odd + tr_even:
                try:
                    name = tr.xpath('td[2]/label')[0]
                    url = tr.xpath('td[3]')[0]
                    status = tr.xpath('td[4]/label')[0]

                    first = name.text.strip()
                    last = name.getchildren()[0].text
                    last = '' if not last else last.strip()

                    date, menu = None, ''
                    try:
                        date = datetime.strptime(status.text.strip(),'%Y-%m-%d')
                        menu_id = url.xpath('a[@class="ez-menu"]')[0].get('name')
                        url = url.xpath('a[@class=""]')[0].get('href').strip() # ValueError
                        menu = menus[menu_id]
                    except ValueError:
                        url = None

                    branch.children['leafs'].append(FileTree.Delivery(first, last, url, date, treeid))
                    branch.children['leafs'][-1].make_menu(menu)

                except IndexError:
                    continue

        else:

            links = xml.xpath('//a[@class="black-link"]')
            menu_ids = xml.xpath('//a[@class="ez-menu"]')

            for link, menu_id in zip(links, menu_ids):
                href = link.get('href')
                menu_id = menu_id.get('name')
                menu = menus[menu_id]
                name = link.text.strip()
                try:
                    tid = int(re.findall('treeid=([0-9]+)', href.decode('utf-8'))[0])
                    branch.children['branches'].append(FileTree.Branch(name, tid, branch))
                    branch.children['branches'][-1].make_menu(menu)
                except:
                    if 'files.phtml' in href:
                        branch.children['leafs'].append(FileTree.Leaf(name, href, branch))
                        branch.children['leafs'][-1].make_menu(menu)

        self.cwd = self.__trees__[treeid] = branch
        

    def print_content(self):

        print(col(self.cwd.path, c.HEAD))
        for items in (self.cwd.children['branches'], self.cwd.children['leafs']):
            for idx, item in enumerate(items):
                print(col('[%-3i] ' % idx, c.HL) + item.str())
        

    def goto_idx(self, idx):

        if idx == '..':
            if self.cwd.parent:
                self.goto_branch(self.cwd.parent)
            return

        idx = int(idx)
        branches = self.cwd.children['branches']
        if idx >= len(branches):
            print(col(' !! not a dir', c.ERR))
            return
        
        self.goto_branch(branches[idx])


    def prepare_form(self, xml):

        form = xml.xpath('//form[@name="actionform"]')[0]
        inputs = form.xpath('input[@type="hidden"]')
        payload = dict((i.name, i.get('value')) for i in inputs)

        url = form.get('action')
        return url, payload


    def upload(self):

        folder = os.getcwd()
        userinput = input('> select a file (%s) : ' % folder)
        
        try:
            assert(os.access(userinput, os.R_OK))
        except AssertionError:
            print(col(' !! cannot read %s' % userinput, c.ERR))
            raise EOFError

        url = self.TARGET +'/links/structureprops.phtml?php_action=file&treeid=%i' % self.cwd.treeid
        response = self.opener.open(url)

        xml = html.fromstring(response.read())
        url, payload = self.prepare_form(xml)

        payload['do_action'] = 'file_save'
        payload['file'] = open(userinput, 'rb')
        self.opener.open(url, payload)
        print(col(' * ', c.ERR) + userinput)


    def download(self, idx, folder = None):

        leaf = self.cwd.children['leafs'][int(idx)]

        if not leaf.url: # Assignments may have no url
            print(col(' !! %s has not uploaded the assignment yet' % leaf.title, c.ERR))
            return

        if not folder:
            folder = self.get_local_folder()

        fname = os.path.basename(leaf.url)
        if self.cwd.is_task:
            fname = '%s_%s' % (leaf.lastname, fname)
        fname = os.path.join(folder, fname)

        with open(fname, 'wb') as local:
            copyfileobj(self.opener.open(self.ROOT + leaf.url), local)
        print(col(' * ', c.ERR) + fname)


    def download_all(self):
        
        nfiles = len(self.cwd.children['leafs'])
        if not nfiles:
            print(col(' !! no files in current dir', c.ERR))
            return
            
        folder = self.get_local_folder()
        for idx in range(nfiles):
            self.download(idx, folder)

    
    def delete(self, idx):

        leaf = self.cwd.children['leafs'][int(idx)]
        if not leaf.url:
            return

        if not 'multi_delete' in leaf.menu:
            print(col(' !! not authorized to delete (%s)' % leaf.title))
            return

        self.opener.open(self.TARGET + '/links/' + leaf.menu['multi_delete'].url)
        print(col(' * ', c.ERR) + leaf.title)


    def delete_all(self):

        nfiles = len(self.cwd.children['leafs'])
        if not nfiles:
            print(col(' !! no files in current dir', c.ERR))
            return
            
        yn = ''
        while yn not in ('y', 'n'):
            yn = input('> delete all in %s? (y/n) ' % self.cwd.path)

        if yn == 'y':
            for idx in range(nfiles):
                self.delete(idx)


    @staticmethod
    def print_eval(xml, evals):

        comment = xml.xpath('//input[@name="element_comment_hidden"]')[0]
        if comment.value:
            print(col(xml.xpath('//label[@for="element_comment"]')[0].text, c.HL))
            print('"""\n' + comment.value.strip() + '\n"""')

        grade = xml.xpath('//input[@name="grade_hidden"]')[0]
        grade_label = xml.xpath('//label[@for="grade"]')[0]
        if grade.value:
            print(col(grade_label.text, c.HL) + ' ' + grade.value)

        eval_text = None
        eval_span = grade.getnext().getchildren()[0].getchildren()[0]
        if evals:
            for evali in evals:
                if 'checked' in evali.keys():
                    eval_text = evali.getnext().text
                    break
        else:
            eval_text = eval_span.getparent().getnext().text

        if eval_text:
            print(col(eval_span.text, c.HL) + ' ' + eval_text)


    def evaluation(self, idx, comment = '', grade = '', evaluation = '', batch = False):

        leaf = self.cwd.children['leafs'][int(idx)]
        if not 'new_comment' in leaf.menu:
            print(col(' !! commenting not available (%s)' % f.title))
            return
        
        response = self.opener.open(self.TARGET + '/links/' + leaf.menu['new_comment'].url)
        xml = html.fromstring(response.read())
        evals = xml.xpath('//input[@type="radio"]')

        batch = batch and comment and grade and evaluation

        if not batch: 

            FileTree.print_eval(xml, evals)

            # Check if authorized to edit
            if not evals:
                return

            # Give option to edit
            yn = ''
            while yn not in ('y', 'n'):
                yn = input('> edit evaluation, grade and comment? (y/n) ')

            if yn == 'y':

                evals = [(item.getnext().text, item.get('value')) for item in evals]
                print('')
                for idx, evali in enumerate(evals):
                    print(col('[%-3i] ' % idx, c.HL) + evali[0])
                evaluation = evals[int(input('> evaluation <index> : ').strip())][1]

                grade = input('> grade : ')

                print('> comment (end with Ctrl-D):')
                print('"""')
                while True:
                    try:
                        comment += input('') + '\n'
                    except EOFError:
                        break
                print('"""')

            else:
                return
                
        # Finally, upload stuff

        url, payload = self.prepare_form(xml)

        payload['do_action']       = 'comment_save'
        payload['element_comment'] = comment
        payload['grade']           = grade
        payload['aproved']         = evaluation

        self.opener.open(url, urlencode(payload).encode('ascii'))


    def evaluate_all(self):
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
                print(col(' !! %s does not exist' % userinput, c.ERR))
            else:
                print(col(' !! failed to read %s' % userinput, c.ERR))
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
            print(col(' !! failed to create dir', c.ERR))
            raise EOFError

        return folder
