from ananas import *
from .plugins import parse_html

class Survey(Tool):

    class Result(object):

        def __init__(self, firstname, lastname, time, status, score, payload):
        
            self.firstname = firstname
            self.lastname = lastname
            self.title = '%s %s' % (firstname, lastname)
            self.date = col(time.strftime('%m-%d %H:%M'), c.HL, True) if time else col('NA', c.ERR, True)
            self.status = col(status, c.HEAD) if status else col('NA', c.ERR)
            self.score = score if score else 0
            self.payload = payload

        def str(self):
            return '%-21s %-40s %3i%% %s' % (self.date, self.title, self.score, self.status)

    class Page(object):

        Question = namedtuple('Question', ('text', 'answers', 'id'))
        Answer   = namedtuple('Answer'  , ('text', 'id'))

        def __init__(self, ul_xml, pageno):
            
            self.title = ul_xml[0].xpath('//td[@style="vertical-align: top;"]')[0].text.strip()
            self.infotext = parse_html(ul_xml[0])

            self.questions = {}
            self.replies = None

            for i, item in enumerate(ul_xml[1:]):
                no = col('%i.%i' % (pageno, i), c.HL)
                text = parse_html(item)

                fields = item.getnext()
                answers = []
                if fields != None and fields.tag == 'fieldset':
                    for a in fields.xpath('.//input[@type="radio"]'):
                        answers.append(self.Answer(a.text, a.get('id')))

                qid = item.getprevious().get('name')
                self.questions[no] = self.Question(text, answers, qid)

        def str(self):
            return self.title[:60] + (' ...' if len(self.title) > 60 else '')

        def do(self):

            print(col(self.infotext, c.HL) + '\n')
            for no, q in self.questions.iterkeys():
                print(no + ' ' + q.text)
                for i, a in enumerate(q.answers):
                    print(col('[%-3i] ' % (i + 1), c.HL) + a)

            reply = ''
            while 1:
                prev = ''
                if self.replies:
                    prev = '(' + col(' '.join(str(i) for i in self.replies), c.HL) + ') '

                try:
                    reply = input('> answer <index index ... > : ' + prev).strip()
                    if not reply and self.replies:
                        break
                    ri = map(int, reply.split()) # ValueError
                    assert(len(ri.split()) == len(self.questions))
                    self.replies = [q.answers[i-1] for i, q in zip(ri, self.questions)] # IndexError
                    break
                except AssertionError:
                    print(col(' !! wrong number of answers given', c.ERR))
                except KeyboardInterrupt: # Catch it: don't break Survey tool loop
                    break

    def __init__(self, opener, title, url, surveyid):

        self.opener = opener
        self.title = title
        self.url = url
        self.treeid = surveyid
        super(Survey, self).__init__()

    def print_results(self):

        print(col(self.title, c.HEAD))
        for idx, item in enumerate(self.results):
            print(col('[%-3i] ' % (idx + 1), c.HL) + item.str())

    def print_pages(self):

        print(col(self.title, c.HEAD))
        for idx, item in enumerate(self.pages):
            print(col('[%-3i] ' % idx, c.HL) + item.str())

    def goto_page(self, idx):
        self.pages[idx].do()

    def take_survey(self):
        
        try:
            for page in self.pages:
                page.do()
        except KeyboardInterrupt: # Catch it: don't break Survey tool loop
            pass


    def submit(self):
        pass

    def str(self):
        return col(self.title, c.HL)
        

    def _parse(self, xml):

        url, payload = self.prepare_form(xml)
        self.form = {'url' : url, 'payload' : payload }
        self.pages = []
        self.results = []

        if not payload['viewall'] == '1': # You are admin

            self.commands['ls'] = Tool.Command('ls', self.print_results, '', 'list results and scores')
            self.results = Survey._parse_admin(xml)

            #     payload['action']       = 'show_test'
            #     payload['viewall']      = '1'
            #     payload['preview_test'] = '1'
            #     payload['ispage']       = '1'
            #     payload['pageno']       = '0'
                
            #     response = self.opener.open(url, urlencode(payload).encode('ascii'))
            #     data = response.read()
            #     xml = html.fromstring(data)

        else:

            self.commands['ls'] = Tool.Command('ls', self.print_pages, '', 'list survey pages')
            self.commands['go']   = Tool.Command('go', self.take_survey, '', 'take survey')
            self.commands['goto'] = Tool.Command('goto', self.goto_page,
                                                 '<index>', 'go to specific page')
            self.commands['post'] = Tool.Command('post', self.submit, '', 'submit answers')

            print(col(' ## loading questions ...', c.ERR))
            items = xml.xpath('//table/tr/td/ul')
            self.pages.append(Survey.Page(items, 0))

            pageno = 1
            npages = int(re.search('Side: [0-9]+/([0-9]+)', xml.text_content()).groups()[0])
            surveyid = int(payload['surveyid'])
            
            while pageno <= npages:
                payload['pageno']   = str(pageno)
                payload['surveyid'] = payload['check_surveyid'] = str(surveyid)
                
                response = self.opener.open(url, urlencode(payload).encode('ascii'))
                data = response.read()
                xml = html.fromstring(data)

                items = xml.xpath('//table/tr/td/ul')[0]
                self.pages.append(Survey.Page(items, pageno))

                pageno   += 1
                surveyid += 1


    @staticmethod
    def _parse_admin(xml):

        tr_odd = xml.xpath('//tr[@class="tablelist-odd"]')
        tr_even = xml.xpath('//tr[@class="tablelist-even"]')

        _tmp = []
        re_data = re.compile('document\.actionform\.(\w+)\.value[\s\'=]+([0-9]+)')

        for tr in tr_odd + tr_even:
            try:
                name   = tr.xpath('td[2]/label')[0] # IndexError (not a test result row)
                time   = tr.xpath('td[3]/label')
                score  = tr.xpath('td[4]/label/img')
                status = tr.xpath('td[5]/label')

                last, first = name.text_content().strip().split(', ')
                replydata = {}

                try:
                    time = datetime.strptime(time[0].text.strip(),'%Y-%m-%d %H:%M:%S') # ValueError
                    replydata = dict(re_data.findall(name.getchildren()[0].get('onclick')))
                    score = int(score[0].get('src').split('percent=')[-1].split('&')[0])
                    status = status[0].text
                except ValueError:
                    time = score = status = None

                result = Survey.Result(first, last, time, status, score, replydata)
                _tmp.append(result)

            except IndexError:
                continue

        return sorted(_tmp, key=lambda x: x.title + str(x.score))
