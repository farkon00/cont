# Variables
Variables in cont need to be firstly declared using their type and their name, like this:
```
var <name> <type>
```
And then to use a variable value we just use its name. Global variables are zero-initialized
```
include std.cn

var x int
var y int
x print // 0
y print // 0
```

But variables aren't really usefull unless you can write data into them.
For that we use `!<name>` syntax, for example
```
var a int
var b int

12 !a
3 !b

a b + print // 15

2 !b
b print // 2
```

## Local variables
If you declare a variable inside a procedure, it will become local.
That means it will allocate the variable on every call using the call stack.
But the variable won't be zero-initialized on every call.

```
include std.cn

proc print_range int:
  var curr int
  !curr
  while curr 0 > do
    curr print
    curr 1 - !curr 
  end
end

1 print_range
2 print_range
4 print_range
```