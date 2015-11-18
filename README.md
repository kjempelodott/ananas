### Fronter shell in Python

The purpose of this is to minimize the number of puppy deaths. Every time you login to the fronter webpage, a puppy dies. Every time you login to fronter with this tool, however, a puppy gets a treat.

* [Requirements](https://github.com/kjempelodott/ananas#requirements)
* [How to use it](https://github.com/kjempelodott/ananas#how-to-use-it)
  * [Members tool](https://github.com/kjempelodott/ananas#members-tool)
  * [FileTree tools](https://github.com/kjempelodott/ananas#filetree-tools)
    * [Navigating](https://github.com/kjempelodott/ananas#navigating)
    * [Download, upload and delete](https://github.com/kjempelodott/ananas#download-upload-and-delete)
    * [Evaluating assignments](https://github.com/kjempelodott/ananas#evaluating-assignments)
    * [Multiple evaluations](https://github.com/kjempelodott/ananas#multiple-evaluations)

#### Requirements

* Python >= 2.7
* python-lxml
* (IPython, for filesystem tab completion)

#### How to use it

Run it in the terminal like this:

```
./pyshell
```

It will ask for username and password. If login succeeds, you are asked to select a room:

```
./pyshell 
Username: (kjempelodott) usernameAtFronter
Password: 

return <Ctrl-D>
[0  ] Fellesrom for BIO4600 og BIO9600 2014-vår
[1  ] UNIK4450/9450 - Fellesrom 2014-høst
[2  ] FYS1000 - Fellesrom 2014-vår
[3  ] FYS2150 - Fellesrom 2014-vår
[4  ] FYS2150L - Fellesrom 2014-vår
[5  ] FYS2150 - Fellesrom 2015-vår
[6  ] FYS2150L - Fellesrom 2015-vår
> select a room <index> :
```

Currently, there are two tools implemented: Members and FileTree. After selecting a room, you will be asked to select a tool:

```
> select a room <index> : 5
 * FYS2150 - Fellesrom 2015-vår

return <Ctrl-D>
[0  ] Deltakere
[1  ] Kursmat. og prelab
[2  ] Rapportinnlevering
[3  ] Lego Watt-vekt
> select a tool <index> :
```

Note that you can always go back by pressing `Ctrl-D`. While inside a tool, you can exit the pyshell by typing `exit`. To abort an interactive command like `mail` or `eval`, press `Ctrl-C`.

#### Members tool

In the example above, the first entry is a Members tool while the last three are FileTree tools. Choosing the Members tool (index 0), we are presented with a help text listing all available commands:

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

The Members tool lets you list all members of the room and compose an email to one or a group of member(s). Before you try to send emails, please make sure that the correct server, domain and port are set in `fronter.conf`. Let's list all the members:

```
> ls
[0  ] Tro, Lo                             lol@jiofwq.com                     eier
[1  ] Blarg, Blæh                         blah@nfiha.com                     slette
[2  ] Ku, Mø                              møøø@nifwq.com                     skrive
[3  ] Flofsesen, Flofs                    flofs@djoifq.com                   skrive
>
```

The last column shows the group label. The `mail` command can either take a space separated list of indices or a label as argument. It also understands inverse label selection, `![label]`. Examples:

```
> mail 0 3     # selects 0 and 3
> mail !skrive # selects 0 and 1
> mail eier    # selects 0
```

#### FileTree tools

The FileTree tools allows you to traverse folders, and list, download, delete, upload and evaluate files:

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

##### Navigating

The `ls` and `cd` commands are similar to the shell commands. Note that `ls` does not take any arguments. It only list the contents of the current directory. Let's try it:

```
> ls
/
[0  ] Kursinfo
[1  ] Matlab
[2  ] test
[3  ] readme.txt                                                   eval, del, get
> 
```

Directories are shown in bold text (well, obviously not in this README ... ). To go up one directory, type `cd ..`. But since we're already at root, let's enter the **test** (index 2) directory:

```
> cd 2
> ls
/test/
[0  ] SG5Vspreg.pdf                                                eval, del, get
[1  ] IR_TXRX_EXTREFLCT.pdf                                        eval, del, get
[2  ] ExtreflctParts.txt                                           eval, del, get
>
```

##### Download, upload and delete

The rightmost column shows the available actions for each file. The `eval` command is really only useful for assignments, so we will skip that for now. The `del` and `get` commands deletes or downloads the file. They take either a list of indices or wildcard * as argument. The wildcard selects all files for download/deletion. For download, you will be asked where to download the files:

```
> get 0
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
[0  ] SG5Vspreg.pdf                                                eval, del, get
```

Wohoo! Note that file select accepts wildcards. For example, `./blah/*.pdf` will upload all pdf-files from `./blah/`.

If you have IPython installed, you will probably find its tab completion capabilities useful for selecting a folder and for uploading files.

##### Evaluating assignments

As mentioned before, `eval` is intended for assigments. This lets admins evaluate, grade and comment on student assigments. Let's go back and choose a FileTree with deliveries:

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
[0  ] NA          Lo Tro                        NA
[1  ] 2015-02-13  Mø Ku				not evaluated
[2  ] NA          Blæh Blarg                    NA
[3  ] NA          Flofs Flofsesen               NA
>
```

Note that if you're a student, you will only see your own assigment, and you will only be able to **read** the evaluation. There is only one student that has uploaded her assigment ... To download it, type `get 1`. Okay, looks like a nice assigment. Let's evaluate it:

```
> eval 1
Evaluering: Ikke evaluert
> edit evaluation, grade and comment? (y/n) y

[0  ] Godkjent
[1  ] På god vei
[2  ] Ikke godkjent
[3  ] Ikke levert
[4  ] Ikke evaluert
> evaluation <index> : 0
> grade : A
> comment (end with Ctrl-D):
"""
Nice work!
"""
> upload file with comments? (leave blank if not)
> select file(s) (/home/myuser) : 
>
```

It is often convenient to write comments directly in the assignment (e.g. by using a pdf editing tool), instead of referring to this page and that line and so on. The last prompt lets you upload a file. Just leave it blank if you only want to leave a text comment. 

##### Multiple evaluations

To automate the evaluation process even further, you can use the `eval#` command. It will take an xml as input. It must comply to the following format:

```
<THISTAGCANBEWHATEVERYOUWANT>
  <student name="Tro Lo" grade="" eval="Godkjent">
    <file>
       "/home/myuser/fronter/tro_lo_comments.pdf"
    </file>
    <comment>
      "Some additional comments ..."
    </comment>
  </student>
  
  <student ...
  ...

</THISTAGCANBEWHATEVERYOUWANT>
```

The only required attribute is `name`. You will get a warning if both `file` and `comment` are missing. If you are too stupid to correctly spell the name or evaluation string, fuzzy string matching will probably save your ass.

#### TODO

* Make a test tool? Maybe daunting, but tempting