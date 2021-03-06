# Cont

__Cont__ is compiled statically-typed concatenative programming language, that has elements of OOP, written in Python and heavily inspired by [Porth](https://gitlab.com/tsoding/porth).

## Where did name come from
From word concatinative. 
How i came up with that specific word?
I just mixed beggining of this word and tried to came up with something sounding good.

# Quick Start
```console
$ python -V
 Python >=3.10
$ git clone https://github.com/farkon00/cont.git
$ cd cont
$ python cont.py <source_code>.cn -r
```

# Examples
You can find more examples in `tests` or `examples` folders.

## Hello world
```
include std.cn

"Hello, world!\n" puts
```

## Fibonacci Numbers
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

## Memories

```
include std.cn

memory a 16

12 a !
a @ print
76 a 8 ptr+ !8
a 8 ptr+ @ print

proc local:
  memory b 8
  2123 b !8
  b @ print
end

local
```

# Arrays
```
include std.cn

const coords_len 69 end

struct Vector2
  int x
  int y
end

init var coords [coords_len] Vector2

42 68 coords [] !x
420 12 coords [] !x
68 coords [] .x print
12 coords [] .x print
4 2 Vector2 23 coords *[] ! // Writes new Vector in 24th array element
```

## Structures
Structures technically support OOP in cont. It doesn't have some really advanced features like interface, generics, but there is moves in that direction like dunder methods or static methods. 

```
struct Vector2
  int x
  int y
end

struct (Vector2) Vector3
  int z
end

proc [Vector2] 3diffy -> Vector3:
  bind self:
    self .x self .y 0
    Vector3
  end
end

42 69 Vector2 .3diffy
.x print
// Btw you can call 3diffy on Vector3
```
