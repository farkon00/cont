# Procedures

Usually, you want to break up your code into reusable pieces, procedures can help you with that.
You might have heard them being called functions or subroutines before.
The syntax for procedures looks like this.

```
proc <name> <type_arg1> <type_arg2>... -> <return_arg1> <return_arg2>...:
  <code>
end
```

There is quite a bit of code there, so let me explain.
Firstly we use the keyboard `proc` to declare a procedure, then we give it a name.
After that, we need to provide the information for the type checker.
You provide types, that the procedure takes as arguments first and then types,
that your procedure will have on the stack at the end of the procedure.
For example, if you have `int int -> int`, that's a type signature for a procedure,
that takes two numbers and returns one. Then we use a column to indicate,
that signature has ended. Then you put the body of the procedure and close it with the `end` keyword.

An example of a simple procedure:
```
proc reverse_subtract int int -> int:
  swap -
end
```

But the procedure itself doesn't do anything, we need to call it.
We use the name of the procedure to call it.
```
3 6 reverse_subtract // [3]
1 5 reverse_subtract // [3 4]
reverse_subtract     // [1]
```

As you can see, now you can reuse your code. Now let's look deeper into procedure syntax.
Return types are optional, so the definition `proc print int: ... end` is completely valid
if you don't need to return anything. Also, the whole signature is optional
if your procedure neither accepts nor returns anything. For example:
```
include std.cn

proc hello_world:
  "Hello world" println // Prints hello world and a new line into the terminal
end

hello_world hello_world hello_world // Calling the procedure three times
```

## Named procedures
If you want to make the most comfortable argument order for the user of the procedure,
sometimes it might be really uncomfortable to use inside the procedure itself.
Or sometimes to not deal with the stack you may find yourself using bind right at the beginning of the procedure.
Named procedures can solve this problem for you. To use named procedures use the `nproc` keyword.
```
// Be careful, if you include std.cn the name 2dup will already be taken
nproc 2dup int first int second -> int:
  first second first second
end
```
This code is equivalent to
```
proc 2dup int int -> int:
  bind first second:
    first second first second
  end
end
```