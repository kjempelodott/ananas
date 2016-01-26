### Fronter shell in Python

The purpose of this is to minimize the number of puppy deaths. Every time you login to the fronter webpage, a puppy dies. Every time you login to fronter with this tool, however, a puppy gets a treat.

* [Requirements](https://github.com/kjempelodott/ananas#requirements)
* [How to use it](https://github.com/kjempelodott/ananas#how-to-use-it)
  * [RoomInfo tool](https://github.com/kjempelodott/ananas#roominfo-tool)
  * [Members tool](https://github.com/kjempelodott/ananas#members-tool)
  * [FileTree tools](https://github.com/kjempelodott/ananas#filetree-tools)
    * [Navigating](https://github.com/kjempelodott/ananas#navigating)
    * [Download, upload and delete](https://github.com/kjempelodott/ananas#download-upload-and-delete)
    * [Evaluating assignments](https://github.com/kjempelodott/ananas#evaluating-assignments)
    * [Multiple evaluations](https://github.com/kjempelodott/ananas#multiple-evaluations)
  * [Survey tool](https://github.com/kjempelodott/ananas#survey-tool)
    * [Taking a survey](https://github.com/kjempelodott/ananas#taking-a-survey)
    * [Read evaluation and comments](https://github.com/kjempelodott/ananas#read-evaluation-and-comments)
    * [Evaluating replies](https://github.com/kjempelodott/ananas#evaluating-replies)

#### Requirements

* Python >= 2.7
* python-lxml
* (IPython, for filesystem tab completion)

#### How to use it

Run it in the terminal like this (\*nix):

```
./pyshell
```

If you're using Windows or whatever, eh ... , try this:

```
python pyshell
```

It will ask for username and password. Your local username will be used if you leave the username field blank. If login succeeds, you are asked to select a room:

```
./pyshell 
Username: (myuser) usernameAtFronter
Password: 

return <Ctrl-D>
[1  ] Fellesrom for BIO4600 og BIO9600 2014-vår
[2  ] UNIK4450/9450 - Fellesrom 2014-høst
[3  ] FYS1000 - Fellesrom 2014-vår
[4  ] FYS2150 - Fellesrom 2014-vår
[5  ] FYS2150L - Fellesrom 2014-vår
[6  ] FYS2150 - Fellesrom 2015-vår
[7  ] FYS2150L - Fellesrom 2015-vår
> select a room <index> :
```

Currently, there are three tools implemented: RoomInfo, Members and FileTree. After selecting a room, you will be asked to select a tool:

```
> select a room <index> : 6
 * FYS2150 - Fellesrom 2015-vår

return <Ctrl-D>
[1  ] Rom
[2  ] Deltakere
[3  ] Kursmat. og prelab
[4  ] Rapportinnlevering
[5  ] Lego Watt-vekt
> select a tool <index> :
```

The first entry is a RoomInfo tool, the second a Members tool and the last three are FileTree tools.

Note that you can always go back by pressing `Ctrl-D`. While inside a tool, you can exit the pyshell by typing `exit`. To abort a command like , press `Ctrl-C`.

Commands that requires text editing, like `put`, `mail` and `eval`, will open up the default text editor. On \*nix systems this is defined in the `VISUAL` and/or `EDITOR` environment variables. If not set, `nano` will be used. The editor will open up a temporary file with prefix `fronter_`. It's **IMPORTANT** that you save to this file.

#### RoomInfo tool

The RoomInfo tool lets you read messages posted by teachers. Teachers will also be able to post new (not implemented yet), edit and delete messages.

```
> select a tool <index> : 1
 * Rom

RoomInfo commands:
return <Ctrl-D>
exit                     exit
h                        print commands
ls                       list messages
get      <index>         print message
put      <index>         edit message
del      <index>         delete message
> 
```

The `ls` command shows all messages in descending order, meaning that the latest messages appear at the bottom:

```
> ls
[1  ] Rapport 1 som skal leveres  13.02. ...                       put, del, get
[2  ] Feil i de to første prelab-oppgavene ...                     put, del, get
[3  ] Vi har funnet ut at siste prelaboppgaven for Lengd ...       put, del, get
[4  ] Undervisningsplan ...                                        put, del, get
```

The last column shows the available actions for each message. The `put` and `del` commands are used to edit or delete and will only be availible to teachers and admins. Plain text and light HTML messages can be viewed in the terminal. Let's have a look at the latest message (index 4):

```
> get 4

Undervisningsplan
Jeg har lagt ut en undervisningsplan for semesteret:
Kursmat. og prelab > 0 Kursinfo  > Undervisningsplan_studentversjon_2015.pdf
Hilsen ******

raw html: file:///tmp/fronter_ZNrjtx.html
```

While this message displays nicely, notice the `raw html` thingy at the bottom. If the message looks like codswallop or you see `!! badass table`, you should open the file-link in your browser to display it properly. 

#### Members tool

The Members tool lets you list all members of the room and compose an email to one or a group of member(s):

```
> select a tool <index> : 2
 * Deltakere

Members commands:
return <Ctrl-D>
exit                     exit
h                        print commands
ls                       list members
mail     <index/label>   send mail to a (group of) member(s)
>
```

Before you try to send emails, please make sure that the correct server, domain and port are set in `fronter.conf`. Let's list all the members:

```
> ls
[1  ] Tro, Lo                             lol@jiofwq.com                     eier
[2  ] Blarg, Blæh                         blah@nfiha.com                     slette
[3  ] Ku, Mø                              møøø@nifwq.com                     skrive
[4  ] Flofsesen, Flofs                    flofs@djoifq.com                   skrive
>
```

The last column shows the group label. The `mail` command can either take a space separated list of indices or a label as argument. It also understands inverse label selection, `![label]`. Examples:

```
> mail 2 3     # selects 2 and 3
> mail !skrive # selects 1 and 2
> mail eier    # selects 1
```

#### FileTree tools

The FileTree tools allows you to traverse folders, and list, download, delete, upload and evaluate files:

```
> select a tool <index> : 3
 * Kursmat. og prelab

FileTree commands:
return <Ctrl-D>
exit                     exit
h                        print commands
ls                       list content of current dir
cd       <index>         change dir
get      <index>         download files
post                     upload files to current dir
del      <index>         delete files
eval#                    upload evaluations from xml
eval     <index>         read and edit evaluation
>
```

##### Navigating

The `ls` and `cd` commands are similar to the shell commands. Note that `ls` does not take any arguments. It only list the contents of the current directory. Let's try it:

```
> ls
/
[1  ] Kursinfo
[2  ] Matlab
[3  ] test
[4  ] readme.txt                                                   eval, del, get
> 
```

Directories are shown in bold text (well, obviously not in this README ... ). To go up one directory, type `cd ..`. But since we're already at root, let's enter the **test** (index 3) directory:

```
> cd 3
> ls
/test/
[1  ] SG5Vspreg.pdf                                                eval, del, get
[2  ] IR_TXRX_EXTREFLCT.pdf                                        eval, del, get
[3  ] ExtreflctParts.txt                                           eval, del, get
>
```

##### Download, upload and delete

The rightmost column shows the available actions for each file. The `eval` command is really only useful for assignments, so we will skip that for now. The `del` and `get` commands deletes or downloads the file. They take either a list of indices or wildcard \* as argument. The wildcard selects all files for download/deletion. For download, you will be asked where to download the files:

```
> get 1
> select folder (/home/myuser) : /tmp/
 * /tmp/SG5Vspreg.pdf
> 
```

Now, let's delete all the crap in **test**:

```
> del *
> delete all in /test/? (y/n) y
 * SG5Vspreg.pdf
 * IR_TXRX_EXTREFLCT.pdf
 * ExtreflctParts.txt
> ls
/test/
> 
```

Let's try to upload some shit:

```
> post
> select file(s) (/home/myuser) : /tmp/SG5Vspreg.pdf
 * /tmp/SG5Vspreg.pdf
> ls
/test/
[1  ] SG5Vspreg.pdf                                                eval, del, get
```

Wohoo! Note that file select accepts wildcards. For example, `./blah/*.pdf` will upload all pdf-files from `./blah/`. Students can use `post` to upload their assignment to a task folder.

If you have IPython installed, you will probably find its tab completion capabilities useful for selecting a folder and for uploading files.

##### Evaluating assignments

As mentioned before, `eval` is intended for assignments. This lets admins evaluate, grade and comment on student assignments. Let's go back and choose a FileTree with tasks:

```
> select a tool <index> : 4
 * Rapportinnlevering

...

> ls
/
[1  ] test
> cd 1
> ls
/test/
[1  ] NA          Lo Tro                        NA
[2  ] 2015-02-13  Mø Ku                         not evaluated
[3  ] NA          Blæh Blarg                    NA
[4  ] NA          Flofs Flofsesen               NA
>
```

Note that if you're a student, you will only see your own assigmnent, and you will only be able to **read** the evaluation. There is only one student that has uploaded her assignment ... To download it, type `get 2`. Okay, looks like a nice assignment. Let's evaluate it:

```
> eval 2
Evaluering: Ikke evaluert
> edit evaluation, grade and comment? (y/n) y

[1  ] Godkjent
[2  ] På god vei
[3  ] Ikke godkjent
[4  ] Ikke levert
[5  ] Ikke evaluert
> evaluation <index> : 1
> grade : A

[ text editor ... ]

> comment:
"""
Nice work!
"""
> upload file with comments? (leave blank if not)
> select file(s) (/home/myuser) : 
>
```

It is often convenient to write comments directly into the assignment (e.g. by using a pdf editing tool), instead of referring to this page and that line and so on. The last prompt lets you upload a file. Just leave it blank if you only want to upload a text comment. 

##### Multiple evaluations

To automate the evaluation process even further, you can use the `eval#` command. It will ask for an xml file. The xml file must comply with the following format:

```
<THISTAGCANBEWHATEVERYOUWANT>
  <student name="Tro Lo" grade="" eval="Godkjent">
    <comment path="/home/myuser/fronter/tro_lo_comments.pdf">
      Some additional comments ...
    </comment>
  </student>
  
  <student ...
  ...

</THISTAGCANBEWHATEVERYOUWANT>
```

The only required attribute is `name`. You will get a warning if both `path` and text are missing in `comment`. If you are too stupid to correctly spell the name or eval string ("Godkjent" or "Ikke godkjent" or whatever ... ), fuzzy string matching will probably save your ass.


#### Survey tool

Surveys are sort of like files and can be accessed from a directory within a FileTree:

```
> ls
/1.1 Tid og frekvens/
[1  ] skript og filer til bruk på lab og prelab
[2  ] Prelab 1. Tid og frekvens
[3  ] tid_frekvens.pdf                                             eval, del, get
```

In the example above, the second entry is a survey. Surveys are listed after directories, but before regular files. Use the `cd` command to enter a survey:

```
> cd 2
Prelab 1. Tid og frekvens
 ## loading questions ...

```

This tool is different for students and admins. Admins can go directly to [Evaluating replies](https://github.com/kjempelodott/ananas#evaluating-replies).

##### Taking a survey

When entering a survey, students are presented with the following menu:

```
Survey commands:
return <Ctrl-D>
exit                     exit
h                        print commands
lr                       list replies and scores
get      <index>         read comments to a reply
ls                       list questions
go                       take survey
goto     <index>         go to specific question
post                     review and submit answers
> 
```

The command `go` takes you through the survey, question by question. At any point, you can press `Ctrl-C` to interrupt. After each question, you will be asked to give an answer. The hint above the prompt tells you whether there is just one correct answer or multiple. If you can't figure out the answer, just press `ENTER` to go to the next question. Some questions are exercises (e.g. write a script), and you will be asked to open an editor with a temporary file. Example:

```
> go

Q #1 Informasjon
some info blabla

Q #2 Spørsmål 1.1. Hvilken påstand er riktig?
[1  ] foo
[2  ] bar
[3  ] baz

one answer
> answer <index> : 1

Q #3 Spørsmål 1.2. Hvilke(t) av forholdene under har innvirkning på
presisjonen i målingene?
[1  ] foo
[2  ] bar
[3  ] baz

multiple choice
> answer <index index ... > : 1 3

Q #4 Skriv et MATLAB-skript som ...

written answer
> open editor? (y/n) n

```

To list all questions, use the command `ls`. The box at the right of each question indicates whether you have given an answer to that question or not. Note that some "questions" are really just pieces of information or whatever, and they will appear as checked questions. Assuming we didn't answer the last exercise (write a script), it should look like this:

```
> ls
[1  ] Informasjon                                                  ... [*]
[2  ] Spørsmål 1.1. Hvilken påstand er riktig?                     ... [*]
[3  ] Spørsmål 1.2. Hvilke(t) av forholdene under har innvirkning  ... [*]
[4  ] Skriv et MATLAB-skript som ...                               ... [ ]
>
```

Question number 4 is missing an answer. To go directly to that question, type `goto 4`. Once you're happy with your answers, submit them with `post`. The list of question will be printed again, but instead of boxes with stars, the rightmost column displays your given answers, for a final review:

```
> post
[1  ] Informasjon                                                  ... 
[2  ] Spørsmål 1.1. Hvilken påstand er riktig?                     ... 1
[3  ] Spørsmål 1.2. Hvilke(t) av forholdene under har innvirkning  ... 1 3
[4  ] Skriv et MATLAB-skript som ...                               ... 
"""
print 'halla'
"""
> submit? (y/n) y
Score: 50%
>
```

Note that text/script exercises have to be evaluated by a teacher; don't despair if the reported score is low.

##### Read evaluation and comments

The `lr` command is like `ls`, but it lists your replies (attempts) instead of questions:

```
> lr
[1  ] 01-19 14:24  Student                                  100% Godkjent
[2  ] 01-18 13:45  Student                                   60% Ikke godkjent
```

If you made any errors, the teacher should leave helpful comments for you. Use the `get` command to print them:

```
> get 2

Poeng: Begreper
Prosentvis poengsum: 100%
Lærerens kommentar til besvarelsen:
Bra!

Poeng: MATLAB-skript
Prosentvis poengsum: 50%
Lærerens kommentar til besvarelsen:
Skiptet fungerer, men det mangler ... bla bla bla

Final score and comments
Prosentvis poengsum: 60%
Lærerens kommentar til besvarelsen:
Du må jobbe litt mer med skriptet
Totalt for prøven: Ikke godkjent
>
```

Note that comments are made per page, not per question, which might be a bit confusing ...

##### Evaluating replies

When entering a survey, admins are presented with the following menu:

```
Survey commands:
return <Ctrl-D>
exit                     exit
h                        print commands
ls                       list replies and scores
get      <index>         read reply, comment on errors and evaluate
eval     <index>         evaluate reply
del      <index>         delete replies
clean                    delete all but the best reply for each student
up                       refresh replies
>
```

To list all replies, use the command `ls`:

```
> ls
[1  ] 01-26 15:43  Student1                                  80.0% Godkjent
[2  ] 01-26 13:38  Student1                                  50.0% Ikke godkjent
[3  ] 01-25 11:36  Student2                                  70.0% NA
[4  ] NA           Student3                                   0.0% NA
```

Student1 has already gotten their reply approved, while Student3 has yet to respond. To read a reply, use the command `get`. Since comments are given per page in Fronter, you will be taken through each page and asked to give a comment. Just leave it blank if there is nothing to comment.

```
> get 3

Q #1 Hvilken påstand er riktig?

Student's answer(s):
* foo

Q #2 Hvilken påstand er riktig?

Student's answer(s):
* bar
* baz

Correct answer(s):
* foo
* baz
> comment : bla bla ...
```

If the student replied correctly to the question, you will just see their answer. If not, the correct answer(s) will be shown as well. Depending on your color scheme, the wrong answers should stand out (in mye terminal: red). Press `ENTER` to continue to the next page:

```
> comment : bla bla ...

  ******

Q #1 Skriv et MATLAB-skript som ...

Student's answer(s):
"""
foo = 2;
bar = 1;
baz = foo + bar;
"""
Score: 0.00
> score (min=0, max=5) : 3
> comment : bla bla ...
```

This page requires the teacher to score manually. The score must be within the `[min, max]` interval printed in the prompt. At the end, you will be shown the total score and asked for a final evaluation/grade and comment.

```
> comment : bla bla ...

  ******

Total score: 15.00/20.00
> evaluation/grade: Godkjent
> final comment : bla bla ...
>
```

In case you just want to do the final evaluation/grading and comment, use the `eval` command. Before you start commenting and evaluating, be sure that you have an updated list of replies. Use the `up` command, which is equivalent to the reload button in your browser.

Students usually have several goes at a survey. The `del` command takes a space separated list of indices as argument and lets you delete all the crappy replies. Even more badass, the `clean` command removes all but the best reply for each student. As a safety precaution, `del` and `clean` print all replies to be deleted and ask for confirmation.