# Loops and conditions

## If
To make conditional code in cont you use the `if` keyword.
There are two syntaxes for ifs you can use any of them,
but the first one is generally recommended.

```
include std.cn

if 1 2 < do // If 1 is smaller than 2
  42 print // Output the number 42 and a new line into the terminal
end // End if
```

```
include std.cn

1 2 < if // If 1 is smaller than 2
  42 print // Output the number 42 and a new line into the terminal
end // End if
```

Ifs take one integer from the stack(or with the first syntax the value gets poped at `do`).
And if the integer is != 0, it executes the code in the block, that ends with the `end` keyword.
Thus comparison operations return integers. There are 6 comparison operation: `==`, `!=`, `>`, `<`, `>=`, `<=`.

## Else

`else` blocks are used to execute code in case of the if condition being 0.
```
5
if dup 2 % 0 == do // If the number on the stack is even
  2 +
else // If the number is odd
  1 +
end
// We will end up with 6 on the stack
```

## Type checking
If you experimented with if and if-else you might have encountered a compilation error similar to the following
```
Error foo:7:3: stack has extra elements in different routes of if-else
Types: int
```
This is an error coming from the type checker. It checks,
that branches of the if-else have the same number of elements on the stack and
that these elements have the same type(we are going to cover types later).
In case there is no `else`, it checks that types with and without executing the if block are the same.

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
In the second example `end` consumes one integer from the stack, if it's != 0 it will start the next iteration.

The same type checking rules apply to the while as to the if. The type stack with and without executing while's body must be the same.
