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
You can find more examples in `tests` or `examples` folders or in the standard library source, which can be found in `std`.

## Hello world
```
include std.cn

"Hello, world!" println
```

## Fibonacci Numbers
```
include std.cn

0 1 50 
while dup 0 > do
  bind prev2 prev num:
    prev
    prev2 prev +
    dup print
    num 1 -
  end
end
```

## Memories

Memories aren't recomended to use, because they don't have type safety in most cases you will want to use variables.

```
include std.cn

memory a 16 // Global memory of size 16 bytes

12 a ! // Write 12 to first 8 bytes a
a @ print // Read value of first 8 bytes of a
76 a 8 ptr+ !8 // Write 76 to 9th byte of a
a 8 ptr+ @ print // Read 8 bytes from a+8

proc local:
  memory b 8 // Local memory of size 8 bytes
  2123 b !8 // Write 2123 to first byte of b(there will be overflow)
  b @ print // Read first 8 bytes of b
end
```

# Arrays
```
include std.cn

const coords_len 69 end

struct Vector2
  int x
  int y
end

init var coords [coords_len] Vector2 // Create array of Vector2 with size coodrs_len and init all of the pointers to the structure 

42 68 coords [] !.x // Write 42 into x of 69th element of array
420 12 coords [] !.x // Write 420 into x of 13th element of array
68 coords [] .x print // Read x of 69th element of array
12 coords [] .x print // Read x of 13th element of array
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

// If you use named procedure owner of the method will be binded to self
nproc [Vector2] 3diffy -> Vector3:
  self.x self.y 0
  Vector3
end

42 69 Vector2 .3diffy // Call a 3diffy on newly created vector
.x print // Print x field of return value of 3diffy
// Btw you can call 3diffy on Vector3
```
