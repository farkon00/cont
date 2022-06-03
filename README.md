# Cont

__Cont__ is compiled concatenative programming language written in Python and heavily inspired by [Porth](https://gitlab.com/tsoding/porth).  

# Examples
## Hello world
```
include std.cn

"Hello, world!\n" puts
```

## Fibanacci numbers
```
0 1 150 
1 while
  bind prev2 prev num:
    prev
    prev2 prev +
    dup print
    num 1 -
    dup 0 >
  end
end
```
