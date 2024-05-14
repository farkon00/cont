# Binds

Binds are a way to give a name to a value. Bindings are immutable and can only be changed after they go out of scope.
Binds has the following syntax.

```
<values>
bind <bind_name1> <bind_name2> <bind_name3>:
  <code here>
end
```

To access bound values you will need to push them onto the stack using their name.

```
1
// Duplicates 1 on the stack
bind value:
  value value
end
```

You can see, that bind will pop the values off the stack and has an ability to bind multiple values.
```
1 2 3
bind first second third:
  second first +   // [3]
  third *          // [9]
  12 swap - // 12 - 9 [3]
end
// Equivalent to dup print 
bind result:
  result print result
end
```

You might have seen, that some of the examples could have just used stack operations,
which you've learned in [lesson 2](https://github.com/farkon00/cont/blob/master/learn-cont/02-basic-operations.md).
And yes they could have, but if you have more than 4 values on the stack,
then you probably shouldn't use stack operations unless absolutely needed.
You can't access anything beyond the 4th element without popping some.
Also bind can usually produce cleaner code, so it's recommended,
unless you just need to perform 1-2 stack operations.

## Let bindings
Sometimes the nesting introduced by bind blocks can be annoying or ugly.
In such a case you can use the `let` keyword, which will bind a value until
the end of the current block. So for example
```
1 2 + let res1;
3 4 + let res2;
res1 res2 + // 10
```
But remember the values will get unbound as soon as the block closes
```
5
if 4 3 > do
  1 + let a;
end
a // compilation error: unknown token
``` 

### Examples
This is the program, that prints the first 50 [Fibonacci numbers](https://en.wikipedia.org/wiki/Fibonacci_number)
using a bind inside a while loop.
```
include std.cn

0 print 1 print

0 1 48 
while dup 0 > do
  bind prev2 prev num:
    prev
    prev2 prev +
    dup print
    num 1 -
  end
end
```