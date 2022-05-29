# Cont

__Cont__ is compiled concatenative programming language written in Python and heavily inspired by [Porth](https://gitlab.com/tsoding/porth).  

# Examples
## Hello world
```
memory str 16

proc str+ int -> ptr:
  str *int + *ptr
end

72 str !8
101 1 str+ !8
108 2 str+ !8
108 3 str+ !8
111 4 str+ !8
44 5 str+ !8
32 6 str+ !8
119 7 str+ !8
111 8 str+ !8
114 9 str+ !8
108 10 str+ !8
100 11 str+ !8
33 12 str+ !8
10 13 str+ !8


14
str
1
1 syscall3
```

## Fibanacci numbers
```
0 1 150 
1 while
  rot swap dup 
  rot + swap
  dup print
  rot 1 - 
  dup 0 > 
end 
```