# Cont

__Cont__ is compiled concatenative programming language written in Python and heavily inspired by [Porth](https://gitlab.com/tsoding/porth).  

# Examples
## Hello world
```
memory str 16

72 str !8
101 str *int 1 + *ptr !8
108 str *int 2 + *ptr !8
108 str *int 3 + *ptr !8
111 str *int 4 + *ptr !8
44 str *int 5 + *ptr !8
32 str *int 6 + *ptr !8
119 str *int 7 + *ptr !8
111 str *int 8 + *ptr !8
114 str *int 9 + *ptr !8
108 str *int 10 + *ptr !8
100 str *int 11 + *ptr !8
33 str *int 12 + *ptr !8
10 str *int 13 + *ptr !8


14
str
1
1 syscall3
```