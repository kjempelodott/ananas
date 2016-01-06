from ananas import *
from .plugins import Mailserver


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
