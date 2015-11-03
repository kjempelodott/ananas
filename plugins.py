import sys, base64
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if sys.version_info[0] == 2:
    from ConfigParser import ConfigParser
    input = raw_input
else:
    from configparser import ConfigParser


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


class Mailserver(smtplib.SMTP_SSL, object):

    def __init__(self, user, secret):

        try:
            conf = ConfigParser()
            conf.read('fronter.conf')
            self.domain = conf.get('email', 'domain').strip('\'')
            self.server = conf.get('email', 'server').strip('\'')
            self.port = int(conf.get('email', 'port').strip('\''))

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

        print('> message (end with Ctrl-D):')
        print('"""')
        while True:
            try:
                text += input('') + '\n'
            except EOFError:
                break
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
