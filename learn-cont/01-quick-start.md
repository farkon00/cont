# Quick start

Run the following commands to setup cont:
```bash
$ python3 -V
 Python >=3.10

$ git clone https://github.com/farkon00/cont.git
$ cd cont

$ sudo apt install fasm # Install fasm with your package manager
$ python3 -m pip install pytest
$ pytest test.py

$ python3 cont.py <source_code>.cn -r
```

# Hello world

How let's write your first hello world in cont:
```
include std.cn

"Hello world" println
```

Now you can run it using this command:
```bash
$ python3 cont.py hello_world.cn -r
```