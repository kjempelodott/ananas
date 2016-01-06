from ananas import *
from .plugins import parse_html


class RoomInfo(Tool):

    unesc = HTMLParser().unescape

    class Message:

        def __init__(self, header, mid, url = None):

            self.header = header
            self.id = mid
            self.url = url
            self.content = ''
            self.html = None
            self.fname = ''
            self.menu = {'get' : url}

        def str(self):
            return '\n' + self.content + col('\nraw html: ', c.HL) + 'file://' + self.fname


    def __init__(self, client, url):

        super(RoomInfo, self).__init__()
        self.opener = client.opener
        self.TARGET = client.TARGET

        self.get_messages(url)
        self.messages = self.messages[::-1]
        self.commands['ls']  = Tool.Command('ls', self.print_messages, '', 'list messages')
        self.commands['get'] = Tool.Command('get', self.view, '<index>', 'print message')
        #self.commands['post'] = Tool.Command('post', self.new, '', 'new message')
        self.commands['put'] = Tool.Command('put', self.edit, '<index>', 'edit message')
        self.commands['del'] = Tool.Command('del', self.delete, '<index>', 'delete message')


    def get_messages(self, url):

        response  = self.opener.open(url + '&show_news_all=1')
        xml       = html.fromstring(response.read())
        msg_tab   = xml.xpath('//table[contains(@class, "news-element")]')[-1]
        msg_id    = msg_tab.xpath('//td[@class="content-header"]/a')
        headers   = msg_tab.xpath('.//div[@class="content-header2"]')
        read_more = msg_tab.xpath('.//div[@style="float:right;"]')
        actions   = msg_tab.xpath('.//div[@class="righttab2"]')

        self.messages = []

        header = mid = ''
        for head, mid, url in zip(headers, msg_id, read_more):
            try:
                header = head.text_content().split('\n', 1)[0][:50]
                mid = mid.get('name').replace('selected_news', '')
                url = self.TARGET + 'prjframe/' + url.getchildren()[0].get('href')
                self.messages.append(RoomInfo.Message(header, mid, url))
            except IndexError:
                self.messages.append(RoomInfo.Message(header, mid))
                self.messages[-1].content = header
                self.messages[-1].fname = RoomInfo._write_html(head)

        if actions:
            for msg in self.messages:
                msg.menu['put'] = self.TARGET + 'prjframe/index.phtml?add_new_news=1&edit_id=' + msg.id
                msg.menu['del'] = self.TARGET + 'prjframe/index.phtml?news_save=1&del_id=' + msg.id


    @staticmethod
    def _write_html(data):
        fd, fname = mkstemp(prefix='fronter_', suffix='.html')
        s  = '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n'
        s += re.sub('</?div.*?>', '', RoomInfo.unesc(html.tostring(data).decode('utf-8')))
        with os.fdopen(fd, 'wb') as f:
            f.write(s.encode('utf-8'))
        return fname


    def print_messages(self):

        for idx, msg in enumerate(self.messages):
            print(col('[%-3i] ' % (idx + 1), c.HL) +
                  '%-60s %s' % (msg.header + ' ... ', ', '.join(msg.menu)))


    def _get_msg(self, idx):

        idx = int(idx) - 1
        if idx < 0:
            raise IndexError

        return self.messages[idx]


    def new(self):
        pass


    def delete(self, idx):

        msg = self._get_msg(idx)

        if not 'del' in msg.menu:
            print(col(' !! not authorized to delete'), c.ERR)
            return

        self.opener.open(msg.menu['del'])


    def edit(self, idx):

        msg = self._get_msg(idx)

        if not 'put' in msg.menu:
            print(col(' !! not authorized to edit'), c.ERR)
            return

        if not msg.fname:
            self.read(msg)

        is_mod = txt.edit(msg.fname)

        if is_mod:
            response = self.opener.open(msg.menu['put'])
            xml = html.fromstring(response.read())
            url, payload = self.prepare_form(xml)

            # Read new message
            with open(msg.fname, 'rb') as f:
                payload['body'] = f.read()

            payload['news_edit'] = msg.id
            self.opener.open(self.TARGET + 'prjframe/' + url, urlencode(payload).encode('ascii'))

            # Refresh and print
            msg.html = None
            msg.content = ''
            self.view(idx)
            msg.header = msg.content.split('\n', 1)[0][:50]


    def read(self, msg):

        response = self.opener.open(msg.menu['get'])
        xml = html.fromstring(response.read())
        _link = xml.xpath('//a[@name="selected_news%s"]' % msg.id)[0]
        msg.html = _link.getnext().xpath('.//div[@class="content-header2"]')[0]
        msg.fname = RoomInfo._write_html(msg.html)


    def view(self, idx):

        msg = self._get_msg(idx)
        if msg.content:
            print(msg.str())
            return

        if msg.html is None:
            self.read(msg)

        # Some short messages are just plain text
        msg.content = msg.html.text or ''

        # Parse HTML
        msg.content = parse_html(msg.html)
        print(msg.str())
