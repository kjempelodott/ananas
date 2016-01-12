import json
from itertools import groupby
from fronter import *
from .plugins import parse_html, wrap


class Survey(Tool):

    class Reply(object):

        Data = namedtuple('Data', ('delete', 'show'))

        def __init__(self, firstname, lastname, time, status, score, data):
        
            self.firstname = firstname
            self.lastname = lastname
            self.title = '%s %s' % (firstname, lastname)
            self.date = col(time.strftime('%m-%d %H:%M'), c.HL, True) if time else col('NA', c.ERR, True)
            self.status = status
            self.score = score if score else 0
            self.data = data

        def str(self):
            return '%-21s %-40s %3i%% %s' % (self.date, self.title, self.score,
                                    col(self.status, c.HEAD) if self.status else col('NA', c.ERR))


    class Question():

        CHECKED   = col('[', c.ERR) + col('*', c.HL) + col(']', c.ERR)
        UNCHECKED = col('[', c.ERR) + ' ' + col(']', c.ERR)

        Answer    = namedtuple('Answer', ('text', 'value', 'correct', 'max_score'))
        Answer.__new__.__defaults__ = (False, 0)

        Hints     = {'radio'    : 'one answer',
                     'checkbox' : 'multiple choice',
                     'textarea' : 'written answer'}

        Prompts   = {'radio'    : 'answer <index> :',
                     'checkbox' : 'answer <index index ... > :',
                     'textarea' : 'open editor (y/n)'}

        def __init__(self, text, idx, answers = [], qtype = None):

            self.text = text
            self.idx = idx
            self.answers = answers
            self.qtype = qtype

            self.title = text.split('\n')[0]
            self.hint = Survey.Question.Hints.get(qtype, '')
            self.prompt = Survey.Question.Prompts.get(qtype, '')
            self._len = 1 if self.qtype == 'radio' else len(self.answers)

            self._given_answer = ''
            self._submit = []
            self.checkbox = Survey.Question.UNCHECKED if self._len else Survey.Question.CHECKED


        def str(self, show_answer=False):
            return '%-60s ... ' % self.title[:60] + (self.checkbox if not show_answer else
                    (col(self._given_answer, c.HEAD) if self.qtype != 'textarea' else \
                     col('\n"""\n%s\n"""' % self._given_answer, c.HEAD)))


        def ask(self):

            print('\n' + col('Q #%i ' % self.idx, c.HL) + col(self.text, c.DIR))
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
                    assert(len(ix) and len(ix) <= self._len)
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


    def __init__(self, opener, TARGET, title, url, surveyid):

        self.opener = opener
        self.TARGET = TARGET
        self.title = title
        self.url = url
        self.treeid = surveyid
        super(Survey, self).__init__()

        self.npages = 0
        self.pages = {}
        self.questions = {}
        self.replies = []
        self._dirty = False


    def str(self):
        return col(self.title, c.HL)


    def print_replies(self):
        for idx, reply in enumerate(self.replies):
            print(col('[%-3i] ' % (idx + 1), c.HL) + reply.str())


    #TODO
    def evaluate(self, idx):

        idx = int(idx) - 1
        if idx < 0:
            raise IndexError

        payload = dict((k,v) for k,v in self.replies[idx].data.show.items())

        for surveyid, questions in self.pages.items():
            payload['surveyid'] = surveyid
            response = self.opener.open(self._url, urlencode(payload).encode('ascii'))
            xml = html.fromstring(response.read())
            
            for qid, q in questions.items():

                _q = xml.xpath('//a[@name="question%i"]' % qid)[0].getnext()
                    
                if q.qtype == 'textarea':

                    print('\n' + col('Q # ', c.HL) + col(q.text, c.DIR))
                    print('\n' + col('student\'s answer:', c.HL))

                    answer = _q.getparent().find('span').text_content()
                    print(col('"""', c.HL))
                    for line in answer.split('\n'):
                        print line
                    print(col('"""', c.HL))

                else:
                    checked = { int(i.value) for i in _q.xpath('.//input[@checked]') }
                    correct = { aid for aid,a in q.answers.items() if a.correct }
                    if checked == correct:
                        continue

                    print('\n' + col('Q # ', c.HL) + col(q.text, c.DIR))
                    print('\n' + col('correct answer(s):', c.HL))
                    for aid in correct:
                        print(col('* ', c.HL) + q.answers[aid].text)
                
                    print('\n' + col('student\'s answer(s):', c.HL))
                    if not checked:
                        print(col('<blank>', c.ERR))
                        continue
                                                
                    for aid in correct & checked:
                        print(col('* ', c.HL) + q.answers[aid].text)

                    for aid in checked - (correct & checked):
                        print(col('* ' + q.answers[aid].text, c.ERR))

            surveyid += 1


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
            payload += r.data.delete

        response = self.opener.open(self._url, urlencode(payload).encode('ascii'))
        self.read_replies(response)


    def clean(self):

        to_delete = []
        # Reply list is already sorted by key (title)
        for student, replies in groupby(self.replies, lambda r: r.title):
            replies = list(replies)
            if len(replies) > 1:
                to_delete += sorted(replies, key=lambda r: r.score)[:-1]
        self.delete(to_delete)


    def print_questions(self):
        for idx, q in enumerate(self.questions.values()):
            print(col('[%-3i] ' % (idx + 1), c.HL) + q.str())


    def goto_question(self, idx):
        idx = int(idx) - 1
        if idx < 0:
            raise IndexError
        self._dirty = True
        self.questions.values()[idx].ask()


    def take_survey(self):
        self._dirty = True
        for q in self.questions.values():
            q.ask()


    def submit(self, postpone=False):

        payload = [(qid, a.value) for qid, q in self.questions.items() for a in q._submit]

        if postpone: # TODO: check that this actually works (not supported for admin in student mode)
            self._payload['do_action'] = 'postpone_answer'
            payload += [(k,v) for k,v in self._payload.items()]
            self.opener.open(self._url, urlencode(payload).encode('ascii'))
        else:
            self._payload['do_action'] = 'send_answer'
            payload += [(k,v) for k,v in self._payload.items()]
            for idx, q in enumerate(self.questions.values()):
                print(col('[%-3i] ' % (idx + 1), c.HL) + q.str(show_answer=True))

            yn = ''
            while yn not in ('y', 'n'):
                yn = input('> submit? (y/n)? ').strip()
                if yn == 'n':
                    return

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

        self._dirty = False


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

        print(col(' ## loading questions ...', c.ERR))

        if payload['viewall'] != '1': # You are admin

            self.commands['ls']    = Tool.Command('ls', self.print_replies, '',
                                                  'list replies and scores')
            self.commands['eval']  = Tool.Command('eval', self.evaluate, '<index>', 'evaluate reply')
            self.commands['del']   = Tool.Command('del', self.delete_idx, '<index>', 'delete replies')
            self.commands['clean'] = Tool.Command('clean', self.clean, '',
                                                  'delete all but the best reply for each student')
            self._read_questions_and_solutions()
            self.replies = Survey._parse_replies(xml)

        else:

            self.read_replies()

            try:
                self.npages = int(re.search('Side: [0-9]+/([0-9]+)', xml.text_content()).groups()[0])
            except:
                print(col(' !! inactive survey', c.ERR))
                return

            self.commands['ls']   = Tool.Command('ls', self.print_questions, '', 'list questions')
            self.commands['go']   = Tool.Command('go', self.take_survey, '', 'take survey')
            self.commands['goto'] = Tool.Command('goto', self.goto_question,
                                                 '<index>', 'go to specific question')
            self.commands['post'] = Tool.Command('post', self.submit, '', 'review and submit answers')
            self.commands['lr']   = Tool.Command('lr', self.print_replies, '', 'list replies and scores')

            items = xml.xpath('//table/tr/td/ul')
            idx, self.questions = Survey._parse_page(items, 0)

            pageno = 0
            surveyid = int(payload['surveyid'])

            while pageno < self.npages - 1:
                pageno   += 1
                surveyid += 1

                payload['surveyid'] = surveyid
                response = self.opener.open(url, urlencode(payload).encode('ascii'))
                xml = html.fromstring(response.read())

                items = xml.xpath('//table/tr/td/ul')
                idx, questions = Survey._parse_page(items, idx)
                self.questions.update(questions)

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

        questions = OrderedDict()
        for i, xml in enumerate(xmls):
            idx += 1

            # fronter HTML is fucked up
            to_parse = []
            more_text = xml[0].getnext()
            while more_text != None and more_text.tag not in ('textarea', 'fieldset'):
                to_parse.append(more_text)
                more_text = more_text.getnext()

            more_text = xml.getnext()
            while more_text != None and more_text.tag != 'ul':
                to_parse.append(more_text)
                more_text = more_text.getnext()

            text = wrap(xml[0].text_content().strip()) + '\n' + parse_html(to_parse).strip()

            radio = xml.xpath('.//input[@type="radio"]')
            checkbox = xml.xpath('.//input[@type="checkbox"]')
            textarea = xml.xpath('../ul/textarea[@class="question-textarea"]')

            if radio:
                answers = [Survey.Question.Answer(wrap(a.label.text), a.get('value')) for a in radio]
                questions[radio[0].name] = Survey.Question(text, idx, answers, 'radio')
            elif checkbox:
                answers = [Survey.Question.Answer(wrap(a.label.text), a.get('value')) for a in checkbox]
                questions[checkbox[0].name] = Survey.Question(text, idx, answers, 'checkbox')
            elif textarea:
                answers = [Survey.Question.Answer('', textarea[0].get('value'))]
                questions[textarea[0].name] = Survey.Question(text, idx, answers, 'textarea')
                break
            else:
                questions['info_%i' % idx] = Survey.Question(text, idx)

        return idx, questions


    @staticmethod
    def _parse_replies(xml):

        onclick = re.compile("actionform\.([a-z]+)\.value\s?=\s?'?(\w+)'?")
        tr_odd = xml.xpath('//tr[@class="tablelist-odd"]')
        tr_even = xml.xpath('//tr[@class="tablelist-even"]')

        _tmp = []
        re_data = re.compile('document\.actionform\.(\w+)\.value[\s\'=]+([0-9]+)')

        for tr in tr_odd + tr_even:
            try:
                # IndexError (not a test reply row)
                delete = tr.xpath('td[1]/input')
                name   = tr.xpath('td[2]/label')[0]
                time   = tr.xpath('td[3]/label')[0]
                score  = tr.xpath('td[4]/label/img')
                status = tr.xpath('td[5]/label')

                last, first = name.text_content().strip().split(', ')
                data = None

                try:
                    time = datetime.strptime(time.text.strip(),'%Y-%m-%d %H:%M:%S') # ValueError
                    delete_payload = [(item.name, item.get('value')) for item in delete]
                    show_payload   = dict(onclick.findall(name.xpath('./a')[0].get('onclick')))
                    data = Survey.Reply.Data(delete=delete_payload, show=show_payload)
                    score = int(score[0].get('src').split('percent=')[-1].split('&')[0])
                    status = status[0].text
                except ValueError:
                    time = score = status = None

                reply = Survey.Reply(first, last, time, status, score, data)
                _tmp.append(reply)

            except IndexError:
                continue

        return sorted(_tmp, key=lambda x: x.title + str(x.score))


    def _read_questions_and_solutions(self):

        base_url = self.TARGET + 'app/teststudio/author/tests/%i' % self.treeid
        surveyid = self.treeid + 1

        try:
            self.pages = OrderedDict()
            self.opener.addheaders = [('accept', 'applitcations/json')]

            while 1:
                url = base_url + '/pages/%i' % surveyid
                response = self.opener.open(url)
                _questions = json.loads(response.read().replace('\n',''), 'utf-8')['questionIdList']
                questions = OrderedDict()

                for q in _questions:
                    url = base_url + '/questions/%i' % q
                    response = self.opener.open(url)
                    q = json.loads(response.read().replace('\n',''), 'utf-8')

                    _answers = q.get('answers', [])
                    answers = OrderedDict()
                    qtype = q.get('metaType', None)

                    if qtype == 'Text':
                        answers[0] = Survey.Question.Answer('', 0, True, float(q['maxScore']))
                        qtype = 'textarea'

                    elif _answers:
                        for a in _answers:
                            atext   = a['answerText']
                            aid     = a['answerId']
                            correct = a['answerCorrect']
                            answers[aid] = Survey.Question.Answer(wrap(atext), aid, correct)

                    else:
                        continue

                    qtext = q['questionText']
                    qid   = q['id']
                    questions[qid] = Survey.Question(wrap(qtext), 0, answers, qtype)

                if questions:
                    self.pages[surveyid] = questions
                surveyid += 1

        except: # HTTPError, end of pages
            self.opener.addheaders = []


    def clean_exit(self):
        if self._dirty:
            self.submit(postpone=True)
