# Binds

Binds are a way to give a name to value. Bindings are immutable and can only be changed after they go out of the scope.
The bind has following syntax.

```
<values>
bind <bind_name1> <bind_name2> <bind_name3>:
  <code here>
end
```

To access bindinded values you will need to push them onto the stack using their name.

```
1
// Duplicates 1 on the stack
bind value:
  value value
end
```

You can see, that bind will pop the values off the stack. You can also bind multiple values.
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

You might have saw, that some of the examples could have just used stack operations, that you learn in 
[lesson 2](https://github.com/farkon00/cont/blob/master/learn-cont/02-basic-operations.md). And yes they could, but if you have more than 4 values on the stack, that you probably shouldn't unless absolutely needed, you can't really access last ones without popping some, also bind can usually produce cleaner code, so it's recomended unless you just need to perform 1-2 stack operations. 

## Examples
This is the program, that prints 50 first [fibonacci numbers](https://en.wikipedia.org/wiki/Fibonacci_number) using bind inside a while loop
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