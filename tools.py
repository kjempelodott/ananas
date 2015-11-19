import os, sys, re
from datetime import datetime
from glob import glob
from collections import namedtuple, OrderedDict
from shutil import copyfileobj
from lxml import html, etree
from plugins import Mailserver, Color
from difflib import SequenceMatcher

if sys.version_info[0] == 2:
    from urllib import urlencode, unquote_plus
    input = raw_input
else:
    from urllib.parse import urlencode, unquote_plus

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
        self.commands['mail'] = Tool.Command('mail', self.mailto, '<index/label>',
                                             'send mail to a (group of) member(s)')


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
            idx = select.split()
            who = [self.members[int(i)] for i in idx]
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

        def __init__(self, title, treeid, parent = None):

            self.title = title
            self.treeid = treeid
            self.parent = parent
            self.path = '/' if not parent else parent.path + title + '/'
            self.children = { 'leafs' : [], 'branches' : [] }
            self.menu = {}

        def str(self):
            return col(self.title, c.DIR)


    class Leaf(Branch):

        _imp = {'multi_delete' : 'del', 'new_comment' : 'eval', 'get' : 'get'}

        Menu = namedtuple('Menu', ['name', 'url'])

        def __init__(self, title, url, parent):

            self.title = title
            self.url = url
            self.parent = parent
            self.menu = {'get' : None}

        def str(self):
            return '%-60s %s' % (self.title,
                ', '.join([FileTree.Leaf._imp[a] for a  in self.menu.keys()]))

        def make_menu(self, menu = ''):
            for item in menu.split(','):
                try:
                    key, url = item.split('^') # ValueError
                    action = url.split('action=')[1].split('&')[0] # IndexError
                    assert(action in FileTree.Leaf._imp)
                    self.menu[action] = FileTree.Leaf.Menu(name = key.strip('"'), url = url)
                except (AssertionError, ValueError, IndexError):
                    continue


    class Delivery(Leaf):

        def __init__(self, firstname, lastname, url, date, status, parent):

            self.firstname = firstname
            self.lastname = lastname
            self.title = '%s %s' % (firstname, lastname)
            self.url = url
            self.date = col(date.strftime('%Y-%m-%d'), c.HL, True) if date else col('NA', c.ERR, True)
            self.status = col(status, c.HEAD) if status else col('NA', c.ERR)
            self.parent = parent
            self.menu = {}

        def str(self):
            return '%-20s %-40s %s' % (self.date, self.title, self.status)
                

    def __init__(self, client, url):

        self.TARGET = client.TARGET
        self.ROOT = client.ROOT
        self.url = url

        super(FileTree, self).__init__()
        self.opener = client.opener

        self.init_tree()
    
        # Shell-like filesystem stuff
        self.commands['ls'] = Tool.Command('ls', self.print_content, '', 'list content of current dir')
        self.commands['cd'] = Tool.Command('cd', self.goto_idx, '<index>', 'change dir')
        # Download
        self.commands['get']  = Tool.Command('get', self.download, '<index>', 'download files')
        # Upload
        self.commands['post'] = Tool.Command('post', self.upload, '', 'upload files to current dir')
        # Delete
        self.commands['del']  = Tool.Command('del', self.delete, '<index>', 'delete files')
        # Evaluate
        self.commands['eval#'] = Tool.Command('eval#', self.evaluate_all, '', 
                                              'upload evaluations from xml')
        self.commands['eval']  = Tool.Command('eval', self.evaluate, '<index>',
                                              'read and edit evaluation')


    def init_tree(self):
        
        response = self.opener.open(self.url)
        treeid = int(re.findall('root_node_id=([0-9]+)', response.read().decode('utf-8'))[0])
        root = FileTree.Branch('', treeid)
        self.__trees__ = {} # Keeps all branches in memory
        self.goto_branch(root)
    

    def refresh(self):

        self.goto_branch(self.cwd, True)


    def _parse_task(self, xml, menus):

        tr_odd = xml.xpath('//tr[@class="tablelist-odd"]')
        tr_even = xml.xpath('//tr[@class="tablelist-even"]')

        for tr in tr_odd + tr_even:
            try:
                name   = tr.xpath('td[2]/label')[0] # IndexError (not an assigment row)
                url    = tr.xpath('td[3]')[0]
                date   = tr.xpath('td[4]/label')[0]
                status = tr.xpath('td[5]/img')

                first = name.text.strip()
                last  = name.getchildren()[0].text
                last  = '' if not last else last.strip()

                menu = ''
                try:
                    date = datetime.strptime(date.text.strip(),'%Y-%m-%d') # ValueError (not delivered)
                    menu_id = url.xpath('a[@class="ez-menu"]')[0].get('name')
                    url = url.xpath('a[@class=""]')[0].get('href').strip()
                    status = status[0].get('src').split('/')[-1].split('.')[0].replace('_', ' ')
                    menu = menus[menu_id]
                except ValueError:
                    url = date = status = None

                self.cwd.children['leafs'].append(FileTree.Delivery(first, last, url,
                                                                    date, status, self.cwd))
                self.cwd.children['leafs'][-1].make_menu(menu)

            except IndexError:
                continue


    def _parse(self, xml, menus, refresh = False):

        links = xml.xpath('//a[@class="black-link"]')
        menu_ids = xml.xpath('//a[@class="ez-menu"]')

        for link, menu_id in zip(links, menu_ids):
            href = link.get('href')
            menu_id = menu_id.get('name')
            menu = menus[menu_id]
            name = link.text.strip()
            try:
                assert(not refresh)
                tid = int(re.findall('treeid=([0-9]+)', href)[0])
                self.cwd.children['branches'].append(FileTree.Branch(name, tid, self.cwd))
            except AssertionError:
                if 'files.phtml' in href:
                    self.cwd.children['leafs'].append(FileTree.Leaf(name, href, self.cwd))
                    self.cwd.children['leafs'][-1].make_menu(menu)


    def goto_branch(self, branch, refresh = False):

        treeid = branch.treeid
        if treeid in self.__trees__ and not refresh:
            self.cwd = branch
            return

        url = self.TARGET + '/links/structureprops.phtml?treeid=%i' % treeid
        response = self.opener.open(url)
        data = response.read()
        xml = html.fromstring(data)
        branch.is_task = bool(xml.xpath('//td/label[@for="folder_todate"]'))

        menus = dict((mid, menu) for mid, menu in
                     re.findall('ez_Menu\[\'([0-9]+)\'\][=_\s\w]+\(\"(.+)"\)', 
                                data.decode('utf-8')))

        branch.children['leafs'] = []
        self.cwd = branch
        if branch.is_task:
            self._parse_task(xml, menus)
        else:
            self._parse(xml, menus, refresh)

        self.__trees__[treeid] = branch


    def print_content(self):

        print(col(self.cwd.path, c.HEAD))
        for idx, item in enumerate(self.cwd.children['branches'] + self.cwd.children['leafs']):
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
        if not url.startswith(self.TARGET):
            url = self.TARGET + url.lstrip('..')

        return url, payload


    def upload(self, assignment_xml = None, *comments_file):

        files, userinput = [], ''
        if not comments_file:
            folder = os.getcwd()
            userinput = input('> select file(s) (%s) : ' % folder)

        for f in glob(userinput) + list(comments_file):
            try:
                assert(os.access(f, os.R_OK))
                files.append(f)
            except AssertionError:
                print(col(' !! cannot read %s' % f, c.ERR))

        if not files:
            return

        url = ''
        if assignment_xml is not None:
            url = self.TARGET + \
                assignment_xml.xpath('//table[@class="archive-inner"]//a')[-1].get('href').lstrip('..')
        else:
            url = self.TARGET + \
                '/links/structureprops.phtml?php_action=file&treeid=%i' % self.cwd.treeid
        response = self.opener.open(url)

        xml = html.fromstring(response.read())
        url, payload = self.prepare_form(xml)

        payload['do_action'] = 'file_save'
        for f in files:
            payload['file'] = open(f, 'rb')
            self.opener.open(url, payload)
            print(col(' * ', c.ERR) + f)

        self.refresh()


    def download(self, idx):

        idx = idx.strip().split()
        leafs = []
        if idx[0] == '*':
            leafs = self.cwd.children['leafs']
        else:
            leafs = [self._get_leaf(i) for i in idx]

        if not leafs:
            print(col(' !! no files in current dir', c.ERR))
            return

        folder = self._get_local_folder()
        if not folder:
            return

        for leaf in leafs:
            if not leaf.url: # Assignments may have no url
                print(col(' !! %s has not uploaded the assignment yet' % leaf.title, c.ERR))
                continue

            fname = unquote_plus(os.path.basename(leaf.url))
            if self.cwd.is_task:
                fname = '%s_%s' % (leaf.lastname, fname)
            fname = os.path.join(folder, fname)

            with open(fname, 'wb') as local:
                copyfileobj(self.opener.open(self.ROOT + leaf.url), local)
            print(col(' * ', c.ERR) + fname)


    def delete(self, idx):

        idx = idx.strip().split()
        leafs = []
        if idx[0] == '*':
            leafs = self.cwd.children['leafs']
            yn = ''
            while yn not in ('y', 'n'):
                yn = input('> delete all in %s? (y/n) ' % self.cwd.path)
            if yn == 'n':
                return
        else:
            leafs = [self._get_leaf(i) for i in idx]

        for leaf in leafs:
            if not leaf.url:
                continue

            if not 'multi_delete' in leaf.menu:
                print(col(' !! not authorized to delete (%s)' % leaf.title))
                continue

            self.opener.open(self.TARGET + '/links/' + leaf.menu['multi_delete'].url)
            print(col(' * ', c.ERR) + leaf.title)

        self.refresh()


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


    def evaluate(self, idx, comment = '', cfile = None, grade = '', evaluation = '', batch = False):

        leaf = self._get_leaf(idx)
        if not leaf:
            return

        if not 'new_comment' in leaf.menu:
            print(col(' !! commenting not available (%s)' % leaf.title))
            return
        
        response = self.opener.open(self.TARGET + '/links/' + leaf.menu['new_comment'].url)
        xml = html.fromstring(response.read())
        evals = xml.xpath('//input[@type="radio"]')

        if not batch: 

            FileTree.print_eval(xml, evals)

            # Check if authorized to edit
            if not evals:

                # Look for comments file
                cfile = xml.xpath('//a[@target="_blank"]')
                if cfile:

                    url = self.TARGET + cfile[0].get('href').lstrip('..')
                    print('> download file with comments? (interrupt with Ctrl-C)')
                    folder = self._get_local_folder()
                    if not folder:
                        return

                    fileext = os.path.splitext(cfile[0].text)
                    orig    = os.path.splitext(os.path.basename(leaf.url))[0]
                    fname   = '%s_comments%s' % (orig, fileext)
                    fname   = os.path.join(folder, fname)

                    with open(fname, 'wb') as local:
                        copyfileobj(self.opener.open(url), local)
                    print(col(' * ', c.ERR) + fname)

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

                print('> upload file with comments? (leave blank if not)')
                self.upload(xml)

            else:
                return

        else: # Get the correct evaluation
            evaluation = evaluation.lower()
            _cmp = []

            for item in evals:
                _cmp.append(item.getnext().text.lower())
                if evaluation == _cmp[-1]:
                    evaluation = item.get('value')
                    break
            else:
                score = [SequenceMatcher(None, evaluation, item).ratio() for item in _cmp]
                win   = max(score)
                idx   = score.index(win)
                evaluation = evals[idx].get('value')

            if cfile:
                self.upload(xml, cfile)

        # Finally, upload stuff

        url, payload = self.prepare_form(xml)

        payload['do_action']       = 'comment_save'
        payload['element_comment'] = comment.encode('utf-8')
        payload['grade']           = grade
        payload['aproved']         = evaluation

        self.opener.open(url, urlencode(payload).encode('ascii'))

        if not batch:
            self.refresh()


    def evaluate_all(self):

        if not self.cwd.children['leafs']:
            print(col('!! nothing to evaluate', c.ERR))
            return

        folder = os.getcwd()
        userinput = input('> input evaluation file (%s) : ' % folder)
        try:
            batch = []

            with open(userinput, 'r') as f:
                tree = etree.fromstring(f.read())

                for student in tree:

                    name, idx = student.get('name').lower(), None
                    if not name:
                        print(col('!! missing student name', c.ERR))
                        continue

                    _cmp = []
                    for leaf in self.cwd.children['leafs']:
                        _cmp.append(leaf.title.lower())
                        if _cmp[-1] == name:
                            idx, name = len(_cmp) - 1, leaf.title
                    else:
                        score = [SequenceMatcher(None, name, item).ratio() for item in _cmp]
                        win   = max(score)
                        idx   = score.index(win)
                        name  = self.cwd.children['leafs'][idx].title

                    evl     = student.get('eval') or ''
                    grade   = student.get('grade') or ''
                    comment = cfile = ''

                    for elem in student:
                        if elem.tag == 'file':
                            cfile = elem.text or ''
                        elif elem.tag == 'comment':
                            comment = elem.text or ''
                            comment = [line.strip() for line in comment.split('\n')]

                    if not cfile and not comment:
                        print(col('!! no comment or comments file (%s)' % name, c.ERR))

                    print('%-45s %s' % (col(name, c.HL, True), comment[0][:30] + ' ...'))
                    batch.append((idx, '\n'.join(comment), cfile, grade, evl, True))

            yn = ''
            while yn not in ('y', 'n'):
                yn = input('> upload evaluations? (y/n) ')
            if yn == 'n':
                return

            for b in batch:
                self.evaluate(*b)

            self.refresh()
            
        except OSError as oe:
            if (oe.errno == 2):
                print(col(' !! %s does not exist' % userinput, c.ERR))
            else:
                print(col(' !! failed to read %s' % userinput, c.ERR))


    def _get_local_folder(self):

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
            return

        return folder


    def _get_leaf(self, idx):

        idx = int(idx) - len(self.cwd.children['branches'])
        if idx < 0:
            print(col(' !! not a file', c.ERR))
            return

        return self.cwd.children['leafs'][idx]
