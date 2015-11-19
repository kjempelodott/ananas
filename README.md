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

Run it in the terminal like this (*nix):

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
[1  ] Fellesrom for BIO4600 og BIO9600 2014-v�r
[2  ] UNIK4450/9450 - Fellesrom 2014-h�st
[3  ] FYS1000 - Fellesrom 2014-v�r
[4  ] FYS2150 - Fellesrom 2014-v�r
[5  ] FYS2150L - Fellesrom 2014-v�r
[6  ] FYS2150 - Fellesrom 2015-v�r
[7  ] FYS2150L - Fellesrom 2015-v�r
> select a room <index> :
```

Currently, there are two tools implemented: Members and FileTree. After selecting a room, you will be asked to select a tool:

```
> select a room <index> : 6
 * FYS2150 - Fellesrom 2015-v�r

return <Ctrl-D>
[1  ] Deltakere
[2  ] Kursmat. og prelab
[3  ] Rapportinnlevering
[4  ] Lego Watt-vekt
> select a tool <index> :
```

Note that you can always go back by pressing `Ctrl-D`. While inside a tool, you can exit the pyshell by typing `exit`. To abort an interactive command like `mail` or `eval`, press `Ctrl-C`.

#### Members tool

In the example above, the first entry is a Members tool while the last three are FileTree tools. Choosing the Members tool (index 1), we are presented with a help text listing all available commands:

```
> select a tool <index> : 1
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
[1  ] Tro, Lo                             lol@jiofwq.com                     eier
[2  ] Blarg, Bl�h                         blah@nfiha.com                     slette
[3  ] Ku, M�                              m���@nifwq.com                     skrive
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
> select a tool <index> : 2
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

The rightmost column shows the available actions for each file. The `eval` command is really only useful for assignments, so we will skip that for now. The `del` and `get` commands deletes or downloads the file. They take either a list of indices or wildcard * as argument. The wildcard selects all files for download/deletion. For download, you will be asked where to download the files:

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

As mentioned before, `eval` is intended for assigments. This lets admins evaluate, grade and comment on student assigments. Let's go back and choose a FileTree with tasks:

```
> select a tool <index> : 3
 * Rapportinnlevering

...

> ls
/
[1  ] test
> cd 1
> ls
/test/
[1  ] NA          Lo Tro                        NA
[2  ] 2015-02-13  M� Ku                         not evaluated
[3  ] NA          Bl�h Blarg                    NA
[4  ] NA          Flofs Flofsesen               NA
>
```

Note that if you're a student, you will only see your own assigment, and you will only be able to **read** the evaluation. There is only one student that has uploaded her assigment ... To download it, type `get 2`. Okay, looks like a nice assigment. Let's evaluate it:

```
> eval 2
Evaluering: Ikke evaluert
> edit evaluation, grade and comment? (y/n) y

[1  ] Godkjent
[2  ] P� god vei
[3  ] Ikke godkjent
[4  ] Ikke levert
[5  ] Ikke evaluert
> evaluation <index> : 1
> grade : A
> comment (end with Ctrl-D):
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

The only required attribute is `name`. You will get a warning if both `path` and text are missing in `comment`. If you are too stupid to correctly spell the name or evaluation string, fuzzy string matching will probably save your ass.
