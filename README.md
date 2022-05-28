# Cont

__Cont__ is compiled concatenative programming language written in Python and heavily inspired by [Porth](https://gitlab.com/tsoding/porth).  

# Examples
## Hello world
```
memory str 16

72 str !8
101 str 1 + !8
108 str 2 + !8
108 str 3 + !8
111 str 4 + !8
44 str 5 + !8
32 str 6 + !8
119 str 7 + !8
111 str 8 + !8
114 str 9 + !8
108 str 10 + !8
100 str 11 + !8
33 str 12 + !8
10 str 13 + !8


14
str
1
1 syscall3
```