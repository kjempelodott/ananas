import sys, os, stat, base64
import smtplib, mimetypes
from subprocess import call
from tempfile import mkstemp
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.generator import _make_boundary as choose_boundary

if sys.version_info[0] == 2:
    from ConfigParser import ConfigParser
    from urllib2 import HTTPHandler, BaseHandler
    from urllib import urlencode
    input = raw_input
else:
    from configparser import ConfigParser
    from urllib.request import HTTPHandler, BaseHandler
    from urllib.parse import urlencode


class Editor():

    def __init__(self):
        self.editor = os.getenv('VISUAL') or os.getenv('EDITOR') or \
                      ('nano', 'notepad.exe')[sys.platform[:3] == 'win']
        self.editor = self.editor.split()

    def edit(self, fname):
        call(self.editor + [fname])

    def new(self):
        fd, fname = mkstemp(prefix='fronter_')
        self.edit(fname)
        return fd


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
txt = Editor()


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
        with os.fdopen(txt.new(), 'rb') as f:
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


class MultipartPostHandler(BaseHandler):

    handler_order = HTTPHandler.handler_order - 10

    def http_request(self, request):
        data = request.data
        if data is not None and type(data) != bytes:
            files = []
            header = []
            try:
                 for key, value in data.items():
                     if hasattr(value, 'fileno'):
                         files.append((key, value))
                     else:
                         header.append((key, value))
            except TypeError:
                return request

            if not files:
                data = urlencode(header)
            else:
                bnd, data = self.multipart_encode(header, files)
                request.add_unredirected_header('Content-Type', 'multipart/form-data; boundary=' + bnd)
            request.data = data

        return request

    def multipart_encode(self, header, files):
        bnd = choose_boundary()

        buffer = ''
        for key, value in header:
            buffer += '--%s\r\n' % bnd
            buffer += 'Content-Disposition: form-data; name="%s"' % key
            buffer += '\r\n\r\n' + value + '\r\n'
        buffer = buffer.encode('utf-8')

        for key, fd in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = fd.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            tmp = '--%s\r\n' % bnd
            tmp += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename)
            tmp += 'Content-Type: %s\r\n' % contenttype
            tmp += '\r\n'

            fd.seek(0)
            buffer += tmp.encode('utf-8')
            buffer += fd.read()
            buffer += '\r\n'.encode('utf-8')

        end = '--%s--\r\n\r\n' % bnd
        buffer += end.encode('utf-8')
        return bnd, buffer

    https_request = http_request
