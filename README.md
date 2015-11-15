## Fronter shell in Python

Fronter is a teaching platform, and I don't like it. I like Python.

#### Requirements

* Python >= 2.7
* python-lxml
* (IPython, for filesystem tab completion)

#### How to use it

Run it from the terminal like this:

```
./pyshell
```

It will ask for username and password. If login succeeds, you will be asked to select a room:

```
./pyshell 
Username: (kjempelodott) usernameAtFronter
Password: 

return <Ctrl-D>
[0  ] Fellesrom for BIO4600 og BIO9600 2014-v�r
[1  ] UNIK4450/9450 - Fellesrom 2014-h�st
[2  ] FYS1000 - Fellesrom 2014-v�r
[3  ] FYS2150 - Fellesrom 2014-v�r
[4  ] FYS2150L - Fellesrom 2014-v�r
[5  ] FYS2150 - Fellesrom 2015-v�r
[6  ] FYS2150L - Fellesrom 2015-v�r
> select a room <index> :
```

Currently, there are two tools implemented: members and filetree. After selecting a room, you will be asked to select a tool:

```
> select a room <index> : 5
 * FYS2150 - Fellesrom 2015-v�r

return <Ctrl-D>
[0  ] Deltakere
[1  ] Kursmat. og prelab
[2  ] Rapportinnlevering
[3  ] Lego Watt-vekt
> select a tool <index> :
```

In the example, the first one is a members tool while the last three are filetree tools. Choosing the members tool (index 0), we are presented with a help text listing all available commands:

```
> select a tool <index> : 0
 * Deltakere

Members commands:
return <Ctrl-D>
exit                     exit
h                        print commands
ls                       list members
mail     <index/label>   send mail to a (group of) member(s)
> 
```

The members tool lets you list all members of the room and compose an email to one or a group of member(s). Before you try to send emails, please make sure that the correct server, domain and port is set in `fronter.conf`. Let's list all the members:

```
> ls
ls
[0  ] Tro, Lo                             lol@jiofwq.com                     eier
[1  ] Blarg, Bl�h                         blah@nfiha.com                     slette
[2  ] Ku, M�                              m���@nifwq.com                     skrive
[3  ] Flofsesen, Flofs                    flofs@djoifq.com                   skrive
>
```

The last column is the group label. The command `mail` can either take a space separated list of indices or a label as argument. It also understands inverse label selection, `![label]`. Examples:

```
> mail 0 3     # selects 0 and 3
> mail !skrive # selects 0 and 1
> mail eier    # selects 0
```

Note that you can alway go back by pressing `Ctrl-D`. While inside a tool, you can exit the pyshell by typing `exit`. To abort an interactive command like `mail`, press `Ctrl-C`.

The filetree tools allows you to traverse folder, and list, download, delete, upload and evaluate files:

```
> select a tool <index> : 1
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

The commands `ls` and `cd` are similar to the shell commands. Note that `ls` does not take any arguments. It will only list the contents of the current directory. Let's try it:

```
> ls
/
[0  ] **Kursinfo**
[1  ] **Matlab**
[2  ] **test**
[3  ] readme.txt                                                   eval, del, get
> 
```

Directories are shown in bold text. Let's enter the **test** (index 2) directory:

```
> cd 2
> ls
/test/
[0  ] SG5Vspreg.pdf                                                eval, del, get
[1  ] IR_TXRX_EXTREFLCT.pdf                                        eval, del, get
[2  ] ExtreflctParts.txt                                           eval, del, get
>
```

The rightmost column shows the available actions for each file. The command `eval` is really only useful for deliveries, so we will skip that for now. The commands `del` and `get` will either delete or download the file. They will either take a list of indices or wildcard '*' as argument. The wildcard will select all files for download/deletion. For download, you will be asked where to download the files:

```
> get 0
> select folder (/home/siljehra/git/ananas) : /tmp/
 * /tmp/SG5Vspreg.pdf
> 
```

Now, let's delete all the crap in **test**:

```
> del *
> delete all in /testmappe/? (y/n) y
 * SG5Vspreg.pdf
 * IR_TXRX_EXTREFLCT.pdf
 * ExtreflctParts.txt
> ls
/testmappe/
> 
```

Let's try to upload some shit:

```
> post
> select file(s) (/home/siljehra/git/ananas) : /tmp/SG5Vspreg.pdf
 * /tmp/SG5Vspreg.pdf
> ls
/testmappe/
[0  ] SG5Vspreg.pdf                                                eval, del, get
```

Wohoo! Note that file select accepts wildcard. For example, `/home/myuser/blah/*.pdf` will upload all pdf-files from `./blah/`.
       
If you have IPython installed, you will probably find the tab completion useful for selecting a folder and for uploading files.

As mentioned before, `eval` is intended for deliveries. This lets admins evaluate, grade and comment on student deliveries. Let's go back and choose a filetree with deliveries:

```
> select a tool <index> : 2
 * Rapportinnlevering

...

> ls
/
[0  ] test
> cd 0
> ls
/test/
[0  ] NA          Lo Tro
[1  ] 2015-02-13  M� Ku
[2  ] NA	  Bl�h Blarg
[3  ] NA	  Flofs Flofsesen
>
```

Note that if you're a student, you will only see your own assigment, and you will only be able to **read** the evaluation. There is just one student that has uploaded her assigment ... To download it, type `get 1`. Okay, looks like a nice assigment. Let's evaluate it:

```
> eval 1
Evaluering: Ikke evaluert
> edit evaluation, grade and comment? (y/n) y

[0  ] Godkjent
[1  ] P� god vei
[2  ] Ikke godkjent
[3  ] Ikke levert
[4  ] Ikke evaluert
> evaluation <index> : 0
> grade : A
> comment (end with Ctrl-D):
"""
Nice work!
"""
>
```

#### TODO

* Edit multiple eval/grade/comments (e.g. read from xml)
