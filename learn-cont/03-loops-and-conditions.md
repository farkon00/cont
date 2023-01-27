# Loops and conditions

# If
To make conditional code in cont you use if. There are two syntaxes for ifs you can use both, but the first one is generally recomended.

```
include std.cn

if 1 2 < do // If 1 is smaller than 2
  42 print // Output number 42 and a new line into the terminal
end // End if
```

```
include std.cn

1 2 < if // If 1 is smaller than 2
  42 print // Output number 42 and a new line into the terminal
end // End if
```

Ifs take one integers from the stack(or with a first syntax the value gets poped at `do`). And if the integer is != 0, it executes the code in the block, that ends with `end` keyword. Thus comparison operations return integers. There are 6 comparison operation: `==`, `!=`, `>`, `<`, `>=`, `<=`.

# Else

The `else` blocks are used to execute code in case, if condition for `if` wasn't met.
```
5
if dup 2 % 0 == do // If the number on the stack is even
  2 +
else // If the number is odd
  1 +
end
// We will end up with 6 on the stack
```

# Type checking
If you experemented with if and if-else you might have encountered a compilation error similar to this
```
Error foo:7:3: stack has extra elements in different routes of if-else
Types: int
```
This is an error comming from a type checker. It checks, that branches of if-else have the same number of elements on the stack and that this elements have the same type(we are going to cover types later). In case there is no `else`, it checks that types with and without executing the if block are the same.

# While
While block is the way to create loops and repetition in cont, just as ifs it has two different syntaxes.

```
0
while dup 5 < do
  dup print
  1 +
end
```

```
0
dup 5 < while
  dup print
  1 +
  dup 5 <
end
```

The same type checking rules apply to the while as to the if. The type stack with and without executing while's body must be the same.