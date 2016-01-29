from fronter import *


class RoomInfo(Tool):

    class Message:

        def __init__(self, title, mid, url = None):
            self.title = title
            self.id    = mid
            self.url   = url
            self.text  = ''
            self.xml   = None
            self.fname = ''
            self.menu  = {'get' : url}

        def str(self):
            return '\n' + self.text + col('\n\nraw html: ', c.HL) + 'file://' + self.fname


    def __init__(self, client, url):

        super(RoomInfo, self).__init__()
        self.client = client
        self.PATH   = client.TARGET + 'prjframe/index.phtml'
        self.url    = url

        self.get_messages()
        self.commands['ls']   = Tool.Command('ls', self.print_messages, '', 'list messages')
        self.commands['get']  = Tool.Command('get', self.view, '<index>', 'print message')
        #self.commands['post'] = Tool.Command('post', self.new, '', 'new message')
        self.commands['put']  = Tool.Command('put', self.edit, '<index>', 'edit message')
        self.commands['del']  = Tool.Command('del', self.delete, '<index>', 'delete message')


    def get_messages(self):

        xml     = self.get_xml(self.url + '&show_news_all=1')
        msg_tab = xml.xpath('//table[contains(@class, "news-element")]')[-1]
        mids    = msg_tab.xpath('//td[@class="content-header"]/a')
        headers = msg_tab.xpath('.//div[@class="content-header2"]')
        actions = msg_tab.xpath('.//div[@class="righttab2"]')

        self.messages = []

        title = mid = ''
        for header, mid in zip(headers, mids):
            try:
                title = header.text_content().split('\n', 1)[0][:50]
                mid   = mid.get('name').replace('selected_news', '')
                url   = self.PATH + '?show_news_all=&expand=%s#selected_news%s' % (mid, mid)
                msg   = RoomInfo.Message(title, mid, url)
            except IndexError:
                msg       = RoomInfo.Message(title, mid)
                msg.text  = title
                msg.fname = html.to_file(header, add_meta=True)
            self.messages.append(msg)

        if actions:
            for msg in self.messages:
                msg.menu['put'] = self.PATH + '?add_new_news=1&edit_id=' + msg.id
                msg.menu['del'] = self.PATH + '?news_save=1&del_id=' + msg.id

        self.messages = self.messages[::-1]


    def print_messages(self):

        for idx, msg in enumerate(self.messages):
            print(col('[%-3i] ' % (idx + 1), c.HL) +
                  '%-55s %s' % (msg.title + ' ... ', ', '.join(msg.menu)))


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

        self.get(msg.menu['del'])
        self.get_messages()


    def edit(self, idx):

        msg = self._get_msg(idx)

        if not 'put' in msg.menu:
            print(col(' !! not authorized to edit'), c.ERR)
            return

        if not msg.fname:
            self.read(msg)

        is_mod = txt.edit(msg.fname)

        if is_mod:

            xml = self.get_xml(msg.menu['put'])
            payload = self.get_form(xml)

            # Read new message
            with open(msg.fname, 'rb') as f:
                msg.text = f.read()

            payload['body']            = msg.text
            payload['form_is_changed'] = 1
            payload['news_edit']       = msg.id
            self.post(self.PATH, payload)

            # Refresh and print
            msg.xml = None
            msg.text = ''
            self.view(idx)
            msg.title = msg.text.split('\n', 1)[0][:50]


    def read(self, msg):

        xml = self.get_xml(msg.menu['get'])
        link = xml.xpath('//a[@name="selected_news%s"]' % msg.id)[0]
        msg.xml = link.getnext().xpath('.//div[@class="content-header2"]')[0]
        msg.fname = html.to_file(msg.xml, add_meta=True)


    def view(self, idx):

        msg = self._get_msg(idx)
        if msg.text:
            print(msg.str())
            return

        if msg.xml is None:
            self.read(msg)

        # Some short messages are just plain text
        msg.text = msg.xml.text or ''

        # Parse HTML
        msg.text = html.to_text(msg.xml)
        print(msg.str())
