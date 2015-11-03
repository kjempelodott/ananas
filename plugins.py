import sys, base64
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if sys.version_info[0] == 2:
    input = raw_input


class Mailserver(smtplib.SMTP_SSL, object):

    def __init__(self, user, secret):
        super(Mailserver, self).__init__('smtp.uio.no', 465)
        self.login(user, base64.b64decode(secret).decode('ascii'))
        self.me = user + '@mail.uio.no'
        
    def sendmail(self, recipients):

        subject = Header(input('> subject : '), 'utf-8')
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.me
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

        if yn == 'y':

            text = MIMEText(text, 'plain', 'utf-8')
            msg.attach(text)

            print(' ... sending ... ')
            for rec in recipients:
                msg['To'] = rec.email
                print(' * %s' % rec.email)
                super(Mailserver, self).sendmail(self.me, rec.email, msg.as_string())


class Color():
     
    def __init__(self):
        
        self.HEAD = '\033[1;33m'
        self.HL   = '\033[1;36m'
        self.DIR  = '\033[1;34m'
        self.ERR  = '\033[31m'
        self.END  = '\033[0m'
        
    def colored(self, text, style = '\033[m', padding = False):
        return style + text + self.END + padding * ' ' * (8 - len(style))

