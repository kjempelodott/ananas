import sys
import smtplib

if sys.version_info[0] == 2:
    input = raw_input

class Mailserver(smtplib.SMTP_SSL, object):

    def __init__(self, user, secret):
        super(Mailserver, self).__init__('smtp.uio.no', 465)
        self.login(user, secret)
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
