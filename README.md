# Cont

![Static Badge](https://img.shields.io/badge/docs-latest-blue?style=flat&link=https%3A%2F%2Ffarkon00.github.io%2Fcont%2F)

__Cont__ is a compiled statically-typed concatenative programming language,
that has elements of OOP, is written in Python and is inspired by [Porth](https://gitlab.com/tsoding/porth).

## Where did the name come from
From word concatinative. 
How have I come up with that specific word?
I just mixed beginning of that word and tried to come up with something, that sounds good.

# Quick Start

```bash
$ python3 -V
 Python >=3.10

$ git clone https://github.com/farkon00/cont.git
$ cd cont

# Install fasm with your package manager, nodejs and wabt (https://github.com/WebAssembly/wabt) for testing wasm
$ sudo apt install fasm nodejs wabt
$ python3 -m pip install pytest
$ pytest test.py

$ python3 cont.py <source_code>.cn -r
```

# Examples
You can find examples on how to use the language in the `tests` or `examples` folders or
in the standard library source, which can be found in the `std` directory.

Please note that tests are contained in one file, so the only part of the test file,
which contains cont code is the first one, before the first occurence of a line
that contains a single colon symbol and nothing else.
