#Сборка из git-репозитория(Ubuntu x32, Ubuntu x64)

**Внимание!** Сборка будет разбираться на примере Ubuntu 
Для начала необходимо склонировать проект к себе на компьютер:
```
git clone https://bitbucket.org/exonch/ch-sdk && cd ch-sdk
```

Затем необходимо установить `python3.5` и пакетный менеждер `python3-pip`:
```
$ sudo apt-get install python3 python3-pip
```

Далее необходимо установить некоторые системные пакеты(только на Linux):
```
$ sudo apt-get install libxml2-dev libxslt1-dev zlib1g-dev
```

Далее необходимо установить все пакеты из файла requirements.txt:
```
$ sudo pip3 install -r requirements.txt
```

Теперь необходимо сделать сборку выполнив команду:
```
$ python3.5 builder.py build_exe -p queue
```

Далее нужно перейти в директорию со сборкой:
```
$ cd build/exe.*/
```

Файл `chkit` - это bin-файл. Запустить его можно командой:
```
$ ./chkit
```
