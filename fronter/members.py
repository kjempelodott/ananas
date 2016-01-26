import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fronter import *


class Mailserver(smtplib.SMTP_SSL, object):

    def __init__(self, user, secret):

        try:
            conf = ConfigParser()
            conf.read('fronter.conf')
            self.domain = conf.get('email', 'domain').strip('\'')
            self.server = conf.get('email', 'server').strip('\'')
            self.port   = int(conf.get('email', 'port').strip('\''))

            if conf.has_option('email', 'username'):
                self.username = conf.get('email', 'username').strip('\'')
                print('\nConnecting to %s as %s ...' % (self.server, self.username))
                from getpass import getpass
                self.__secret__ = base64.b64encode(getpass().encode('utf-8'))
            else:
                self.username = user
                self.__secret__ = secret
        except:
            print(col(' !! [email] domain/server/port not set in fronter.conf', c.ERR))
            raise KeyboardInterrupt

        self.me = user + '@' + self.domain


    def sendmail(self, recipients):

        subject = Header(input('> subject : '), 'utf-8')
        msg = MIMEMultipart()
        msg['Subject'] = subject

        text = ''
        with os.fdopen(txt.new()[0], 'rb') as f:
            text = f.read()

        print('> message:')
        print('"""')
        print(text)
        print('"""')

        yn = ''
        while yn not in ('y', 'n'):
            yn = input('> send this message? (y/n) ')

        try:
            assert(self.noop()[0] == 250)
        except:
            super(Mailserver, self).__init__(self.server, self.port)
            self.login(self.username, base64.b64decode(self.__secret__).decode('ascii'))

        if yn == 'y':

            text = MIMEText(text, 'plain', 'utf-8')
            msg.attach(text)

            for rec in recipients:
                try:
                    super(Mailserver, self).sendmail(self.me, rec.email, msg.as_string())
                    print(col(' * ', c.ERR) + rec.email)
                except:
                    print(col(' !! failed to send mail', c.ERR))
                    break


class Members(Tool):

    class Member:

        def __init__(self, name, email, label):
            self.name  = name
            self.email = email
            self.label = label.lower()

        # __str__ is broken in Python 2 - tries to encode in ascii
        def str(self):
            return '%-30s %-30s %s' % (self.name[:29], self.email[:29], col(self.label, c.HEAD))

    def __init__(self, client, url):

        super(Members, self).__init__()
        self.mailserver = Mailserver(client.__user__, client.__secret__)
        self.client = client

        self.members = []
        self.get_members(url)

        self.commands['ls']  = Tool.Command('ls', self.print_members, '', 'list members')
        self.commands['mail'] = Tool.Command('mail', self.mailto, '<index/label>',
                                             'send mail to a (group of) member(s)')


    def get_members(self, url):

        xml = self.load_page(url)
        rows = xml.xpath('//tr')

        for row in rows:
            try:
                name  = row.xpath('./td[2]/label/a')[0].text
                email = row.xpath('./td[4]/label/a')
                label = row.xpath('./td[last()]/label')[0].text
                email = '' if not email else email[0].text
                self.members.append(Members.Member(name, email, label))
            except IndexError:
                pass


    def print_members(self):

        for idx, member in enumerate(self.members):
            print(col('[%-3i] ' % (idx + 1), c.HL) + member.str())


    def mailto(self, select):

        who = None
        try:
            idx = select.split()
            who = [self.members[int(i) - 1] for i in idx if i > 0]
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
