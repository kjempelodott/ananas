import sys, base64
import smtplib

if sys.version_info[0] == 2:
    input = raw_input

class Mailserver(smtplib.SMTP_SSL, object):

    def __init__(self, user, secret):
        super(Mailserver, self).__init__('smtp.uio.no', 465)
        self.login(user, base64.b64decode(secret).decode('ascii'))
        self.me = user + '@mail.uio.no'
        
    def sendmail(self, recipients):

        subject = input('> subject : ')
        print('> text (end with Ctrl-D):')
        print('"""')
        message = 'Subject: %s\n' % subject
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
            for rec in recipients:
                print(' * %s' % rec.email)
                super(Mailserver, self).sendmail(self.me, rec.email, message)


class Color():
     
    def __init__(self):
        
        self.HEAD = '\033[1;33m'
        self.HL   = '\033[1;36m'
        self.DIR  = '\033[1;34m'
        self.ERR  = '\033[31m'
        self.END  = '\033[0m'
        
    def colored(self, text, style = '\033[m', padding = False):
        return style + text + self.END + padding * ' ' * (8 - len(style))

