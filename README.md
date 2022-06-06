# Cont

__Cont__ is compiled concatenative programming language written in Python and heavily inspired by [Porth](https://gitlab.com/tsoding/porth).  

# Examples
You can find more examples in tests folder.

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

## Structures
Structures kinda support oop in cont. But dont expect some advenced oop features like interfaces 

```
struct Vector2
  int x
  int y
end

struct (Vector3) Vector2
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
