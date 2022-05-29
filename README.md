# Cont

__Cont__ is compiled concatenative programming language written in Python and heavily inspired by [Porth](https://gitlab.com/tsoding/porth).  

# Examples
## Hello world
```
"Hello, world!\n" 1 1 syscall3
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