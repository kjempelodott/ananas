from itertools import groupby
from fronter import *
from .plugins import parse_html


class Survey(Tool):

    class Reply(object):

        def __init__(self, firstname, lastname, time, status, score, payload):
        
            self.firstname = firstname
            self.lastname = lastname
            self.title = '%s %s' % (firstname, lastname)
            self.date = col(time.strftime('%m-%d %H:%M'), c.HL, True) if time else col('NA', c.ERR, True)
            self.status = status
            self.score = score if score else 0
            self.payload = payload

        def str(self):
            return '%-21s %-40s %3i%% %s' % (self.date, self.title, self.score,
                                    col(self.status, c.HEAD) if self.status else col('NA', c.ERR))


    class Question():

        CHECKED   = col('[', c.ERR) + col('*', c.HL) + col(']', c.ERR)
        UNCHECKED = col('[', c.ERR) + ' ' + col(']', c.ERR)

        Answer    = namedtuple('Answer'  , ('text', 'value'))

        Hints     = {'radio'    : 'one answer',
                     'checkbox' : 'multiple choice',
                     'textarea' : 'written answer'}

        Prompts   = {'radio'    : 'answer <index> :',
                     'checkbox' : 'answer <index index ... > :',
                     'textarea' : 'open editor (y/n)'}

        def __init__(self, text, idx, qid = None, answers = [], qtype = None):

            self.text = text
            self.idx = idx
            self.qid = qid
            self.answers = answers
            self.qtype = qtype

            self.title = text.split('\n')[0]
            self.hint = Survey.Question.Hints.get(qtype, '')
            self.prompt = Survey.Question.Prompts.get(qtype, '')
            self.max = 1 if self.qtype == 'radio' else len(self.answers)

            self._given_answer = ''
            self._submit = []
            self.checkbox = Survey.Question.UNCHECKED if self.max else Survey.Question.CHECKED


        def str(self, show_answer=False):
            return '%-60s ... ' % self.title[:60] + (self.checkbox if not show_answer else
                    (col(self._given_answer, c.HEAD) if self.qtype != 'textarea' else \
                     col('\n"""\n%s\n"""' % self._given_answer, c.HEAD)))


        def ask(self):

            print('\n' + col('Q #%i ' % self.idx, c.HEAD) + self.text)
            if not self.answers:
                return

            if self.qtype != 'textarea':
                for i, ans in enumerate(self.answers):
                    print(col('[%-3i] ' % (i + 1), c.HL) + ans.text)
            print('\n' + col(self.hint, c.ERR))

            while 1:
                prev = ''
                if self._given_answer:
                    if self.qtype == 'textarea':
                        prev = col('"""\n' + self._given_answer + '\n"""\n', c.HL)
                    else:
                        prev = col('(' + self._given_answer + ') ', c.HL)

                try:
                    if self.qtype == 'textarea':
                        yn = ''
                        while yn not in ('y', 'n'):
                            yn = input('%s> %s ' % (prev, self.prompt)).strip()
                            if yn == 'n':
                                return

                        if self._given_answer:
                            if txt.edit(self._textf):
                                with open(self._textf, 'rb') as f:
                                    self._given_answer = f.read().strip()
                        else:
                            fd, fname = txt.new()
                            with os.fdopen(fd, 'rb') as f:
                                self._given_answer = f.read().strip()
                                self._textf = fname

                        text = self.answers.pop().text
                        self.answers.append(Survey.Question.Answer(text, self._given_answer))
                        self._submit = self.answers
                        self.checkbox = Survey.Question.CHECKED
                        return

                    reply = input('> %s %s' % (self.prompt, prev)).strip()

                    if not reply:
                        break

                    ix = list(map(int, reply.split())) # ValueError
                    assert(len(ix) and len(ix) <= self.max)
                    if not all(i > 0 for i in ix):
                        raise IndexError

                    self._submit = [self.answers[i-1] for i in ix] # IndexError
                    self._given_answer = ' '.join(map(str, ix))
                    self.checkbox = Survey.Question.CHECKED
                    break
                except ValueError:
                    print(col(' !! (space separated) integer(s) required', c.ERR))
                except IndexError:
                    print(col(' !! answer out of range', c.ERR))
                except AssertionError:
                    print(col(' !! wrong number of answers given', c.ERR))


    def __init__(self, opener, title, url, surveyid):

        self.opener = opener
        self.title = title
        self.url = url
        self.treeid = surveyid
        super(Survey, self).__init__()
        self.commands['lr'] = Tool.Command('lr', self.print_replies, '', 'list replies and scores')


    def str(self):
        return col(self.title, c.HL)


    def print_replies(self):
        for idx, reply in enumerate(self.replies):
            print(col('[%-3i] ' % (idx + 1), c.HL) + reply.str())


    #TODO
    def get_reply(self, idx):
        idx = int(idx) - 1
        if idx < 0:
            raise IndexError


    def delete_idx(self, idx):

        idx = idx.strip().split()
        to_delete = []
        for i in idx:
            try:
                i = int(i) - 1
                if i < 0:
                    raise IndexError
                to_delete.append(self.replies[i])
            except IndexError:
                continue

        self.delete(to_delete)


    def delete(self, to_delete):

        payload = [('do_action' , 'delete_replies' ),
                   ('action'    , 'show_reply_list'),
                   ('surveyid'  , self.treeid + 1)]

        for r in to_delete:
            payload.extend(r.payload)

        response = self.opener.open(self._url, urlencode(payload).encode('ascii'))
        self.read_replies(response)


    def clean(self):

        to_delete = []
        # Reply list is already sorted by key (title)
        for student, replies in groupby(self.replies, lambda r: r.title):
            replies = list(replies)
            if len(replies) > 1:
                to_delete.extend(sorted(replies, key=lambda r: r.score)[:-1])
        self.delete(to_delete)


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

        for idx, q in enumerate(self.questions):
            print(col('[%-3i] ' % (idx + 1), c.HL) + q.str(show_answer=True))

        yn = ''
        while yn not in ('y', 'n'):
            yn = input('> submit? (y/n)? ').strip()
            if yn == 'n':
                return

        payload = [(k,v) for k,v in self._payload.items()]
        payload.extend([(q.qid, a.value) for q in self.questions for a in q._submit])

        response = self.opener.open(self._url, urlencode(payload).encode('ascii'))
        xml = html.fromstring(response.read())

        for span in xml.xpath('//span[@class="label"]')[::-1]:
            percent = re.search('\d+%', span.text)
            if percent:
                print(col('Score: ' + percent.group(), c.HEAD))
                break
        else:
            print(col(' !! something went wrong', c.ERR))

        self.read_replies()


    def read_replies(self, resp = None):
        if not resp:
            resp = self.opener.open(self._url + '?action=show_reply_list&surveyid=%i'
                                    % (self.treeid + 1))
        xml = html.fromstring(resp.read())
        self.replies = Survey._parse_replies(xml)


    def parse(self, xml):

        url, payload  = self.prepare_form(xml)
        self._url     = url
        self._payload = payload

        if payload['viewall'] != '1': # You are admin

            self.commands['del']  = Tool.Command('del', self.delete_idx, '<index>', 'delete replies')
            self.commands['clean']  = Tool.Command('clean', self.clean, '',
                                                   'delete all but the best reply for each student')

            self.replies = Survey._parse_replies(xml)

            #     payload['action']       = 'show_test'
            #     payload['viewall']      = '1'
            #     payload['preview_test'] = '1'
            #     payload['ispage']       = '1'
            #     payload['pageno']       = '0'
                
            #     response = self.opener.open(url, urlencode(payload).encode('ascii'))
            #     data = response.read()
            #     xml = html.fromstring(data)

        else:

            self.read_replies()

            npages = 0
            try:
                npages = int(re.search('Side: [0-9]+/([0-9]+)', xml.text_content()).groups()[0])
            except:
                print(col(' !! inactive survey', c.ERR))
                return

            # self.commands['get']  = Tool.Command('get', self.get_reply, '<index>',
            #                                      'read comments to a reply')

            self.commands['ls']   = Tool.Command('ls', self.print_questions, '', 'list questions')
            self.commands['go']   = Tool.Command('go', self.take_survey, '', 'take survey')
            self.commands['goto'] = Tool.Command('goto', self.goto_question,
                                                 '<index>', 'go to specific question')
            self.commands['post'] = Tool.Command('post', self.submit, '', 'review and submit answers')

            print(col(' ## loading questions ...', c.ERR))

            items = xml.xpath('//table/tr/td/ul')
            idx, self.questions = Survey._parse_page(items, 0)

            pageno = 0
            surveyid = int(payload['surveyid'])

            while pageno < npages - 1:
                pageno   += 1
                surveyid += 1

                payload['pageno']   = pageno
                payload['surveyid'] = payload['check_surveyid'] = surveyid

                response = self.opener.open(url, urlencode(payload).encode('ascii'))
                xml = html.fromstring(response.read())

                items = xml.xpath('//table/tr/td/ul')
                idx, questions = Survey._parse_page(items, idx)
                self.questions.extend(questions)

            for script in xml.xpath('//script[@type="text/javascript"]')[::-1]:
                submithash = re.search('submithash\.value\s?=\s?"(\w+)";', script.text_content())
                if submithash:
                    payload['submithash'] = submithash.groups()[0]
                    break
            else:
                print(col(' !! failed to get submithash (submit might not work)', c.ERR))

            # Prepare for submit
            payload['test_section'] = payload['surveyid']
            payload['do_action']    = 'send_answer'
            payload['action']       = ''
            # Eh ... apparently a dummy submit is needed
            self.opener.open(url, urlencode(payload).encode('ascii'))

        return True


    @staticmethod
    def _parse_page(xmls, idx):

        questions = []
        for i, xml in enumerate(xmls):
            idx += 1

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

            text = xml[0].text_content().strip() + '\n' + parse_html(to_parse).strip()

            radio = xml.xpath('.//input[@type="radio"]')
            checkbox = xml.xpath('.//input[@type="checkbox"]')
            textarea = xml.xpath('../ul/textarea[@class="question-textarea"]')

            if radio:
                answers = [Survey.Question.Answer(a.label.text, a.get('value')) for a in radio]
                questions.append(Survey.Question(text, idx, radio[0].name, answers, 'radio'))
            elif checkbox:
                answers = [Survey.Question.Answer(a.label.text, a.get('value')) for a in checkbox]
                questions.append(Survey.Question(text, idx, checkbox[0].name, answers, 'checkbox'))
            elif textarea:
                answers = [Survey.Question.Answer('', textarea[0].get('value'))]
                questions.append(Survey.Question(text, idx, textarea[0].name, answers, 'textarea'))
                break
            else:
                questions.append(Survey.Question(text, idx))

        return idx, questions


    @staticmethod
    def _parse_replies(xml):

        tr_odd = xml.xpath('//tr[@class="tablelist-odd"]')
        tr_even = xml.xpath('//tr[@class="tablelist-even"]')

        _tmp = []
        re_data = re.compile('document\.actionform\.(\w+)\.value[\s\'=]+([0-9]+)')

        for tr in tr_odd + tr_even:
            try:
                # IndexError (not a test reply row)
                data   = tr.xpath('td[1]/input')
                name   = tr.xpath('td[2]/label')[0]
                time   = tr.xpath('td[3]/label')[0]
                score  = tr.xpath('td[4]/label/img')[0]
                status = tr.xpath('td[5]/label')[0]

                last, first = name.text_content().strip().split(', ')
                payload = {}

                try:
                    time = datetime.strptime(time.text.strip(),'%Y-%m-%d %H:%M:%S') # ValueError
                    payload = [(item.name, item.get('value')) for item in data]
                    score = int(score.get('src').split('percent=')[-1].split('&')[0])
                    status = status.text
                except ValueError:
                    time = score = status = None

                reply = Survey.Reply(first, last, time, status, score, payload)
                _tmp.append(reply)

            except IndexError:
                continue

        return sorted(_tmp, key=lambda x: x.title + str(x.score))
