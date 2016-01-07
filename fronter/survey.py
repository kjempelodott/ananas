from fronter import *
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


    class Question():

        Answer  = namedtuple('Answer'  , ('value', 'id'))
        Hints   = {'radio'    : 'one answer',
                   'checkbox' : 'multiple choice',
                   'textarea' : 'written answer'}
        Prompts = {'radio'    : 'answer <index>',
                   'checkbox' : 'answer <index index ... >',
                   'textarea' : 'press ENTER to open editor'}

        def __init__(self, text, number, qid, answers = [], qtype = None):

            self.text = text
            self.number = number
            self.answers = answers
            self.qid = qid
            self.qtype = qtype

            self.title = text.split('\n')[0]
            self.hint = Survey.Question.Hints.get(qtype, '')
            self.prompt = Survey.Question.Prompts.get(qtype, '')
            self.max = 1 if self.qtype == 'radio' else len(self.answers)

            self.given_answer = self.__submit__ = None


        def ask(self):

            print('\n' + col(self.number, c.HEAD) + ' ' + self.text + '\n')
            if not self.answers:
                return

            if self.qtype != 'textarea':
                for i, ans in enumerate(self.answers):
                    print(col('[%-3i] ' % (i + 1), c.HL) + ans.value)
                print('\n' + col(self.hint, c.ERR))

            while 1:
                prev = ''
                if self.given_answer:
                    prev = col('(' + self.given_answer + ') ', c.HL)

                try:
                    reply = input('> %s %s: ' % (self.prompt, prev)).strip()
                    if self.qtype == 'textarea':
                        pass
                    if not reply and self.given_answer:
                        break

                    ix = map(int, reply.split()) # ValueError
                    assert(len(ix) <= self.max)
                    if not all(i > 0 for i in ix):
                        raise IndexError

                    self.__submit__ = [self.answers[i-1] for i in ix] # IndexError
                    self.given_answer = ' '.join(map(str, ix))
                    break
                except ValueError:
                    print(col(' !! (space separated) integer(s) required', c.ERR))
                except IndexError:
                    print(col(' !! answer out of range', c.ERR))
                except AssertionError:
                    print(col(' !! wrong number of answers given', c.ERR))


        def str(self):
            return '%-6s %-60s ... %s' % (col(self.number, c.HEAD, True),
                                          self.title[:60],
                                          col('*', c.ERR) if not self.max or self.__submit__ else '')


    def __init__(self, opener, title, url, surveyid):

        self.opener = opener
        self.title = title
        self.url = url
        self.treeid = surveyid
        super(Survey, self).__init__()

        self.questions = []


    def str(self):
        return col(self.title, c.HL)


    def print_results(self):
        print(col(self.title, c.HEAD))
        for idx, result in enumerate(self.results):
            print(col('[%-3i] ' % (idx + 1), c.HL) + result.str())


    def print_questions(self):
        for idx, q in enumerate(self.questions):
            print(col('[%-3i] ' % (idx + 1), c.HL) + q.str())


    def goto_question(self, idx):
        idx = int(idx) - 1
        if idx < 0:
            raise IndexError
        self.questions[idx].ask()


    def take_survey(self):
        for q in self.questions:
            q.ask()


    def submit(self):
        pass


    def parse(self, xml):

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

            npages = 0
            try:
                npages = int(re.search('Side: [0-9]+/([0-9]+)', xml.text_content()).groups()[0])
            except:
                print(col(' !! inactive survey', c.ERR))
                return

            self.commands['ls'] = Tool.Command('ls', self.print_questions, '', 'list questions')
            self.commands['get'] = Tool.Command('get', self.goto_question,
                                                '<index>', 'go to specific question')
            self.commands['go']   = Tool.Command('go', self.take_survey, '', 'take survey')
            self.commands['post'] = Tool.Command('post', self.submit, '', 'review and submit answers')

            print(col(' ## loading questions ...', c.ERR))

            pageno = 0
            surveyid = int(payload['surveyid'])

            items = xml.xpath('//table/tr/td/ul')
            self._parse_page(items, pageno)

            while pageno < npages:
                pageno   += 1
                surveyid += 1

                payload['pageno']   = str(pageno)
                payload['surveyid'] = payload['check_surveyid'] = str(surveyid)

                response = self.opener.open(url, urlencode(payload).encode('ascii'))
                xml = html.fromstring(response.read())

                items = xml.xpath('//table/tr/td/ul')
                self._parse_page(items, pageno)

        return True


    def _parse_page(self, xmls, pageno):

        for i, xml in enumerate(xmls):

            # fronter HTLM is fucked up
            to_parse = []
            more_text = xml[0].getnext()
            while more_text != None and more_text.tag not in ('textarea', 'fieldset'):
                to_parse.append(more_text)
                more_text = more_text.getnext()

            more_text = xml.getnext()
            while more_text != None and more_text.tag != 'ul':
                to_parse.append(more_text)
                more_text = more_text.getnext()

            text = (xml[0].text_content().strip() + '\n' + parse_html(to_parse)).strip()

            radio = xml.xpath('.//input[@type="radio"]')
            checkbox = xml.xpath('.//input[@type="checkbox"]')
            textarea = xml.xpath('../ul/textarea[@class="question-textarea"]')

            qid = xml.getprevious().get('name')
            no = col('%i.%i' % (pageno + 1, i + 1), c.HEAD)

            if radio:
                answers = [Survey.Question.Answer(a.label.text, a.get('id')) for a in radio]
                self.questions.append(Survey.Question(text, no, qid, answers, 'radio'))
            elif checkbox:
                answers = [Survey.Question.Answer(a.label.text, a.get('id')) for a in checkbox]
                self.questions.append(Survey.Question(text, no, qid, answers, 'checkbox'))
            elif textarea:
                answers = Survey.Question.Answer('', textarea[0].get('id'))
                self.questions.append(Survey.Question(text, no, qid, answers, 'textarea'))
                break
            else:
                self.questions.append(Survey.Question(text, no, qid))


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
