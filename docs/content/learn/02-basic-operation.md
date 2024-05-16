# Basic operations

## The stack

Cont is a stack-based language, which means to perform actions
we push parameters onto the stack and pop them for operations.
You can read more about stack data structures [here](https://en.wikipedia.org/wiki/Stack_(abstract_data_type)).

Cont is whitespace significant in most cases, which means it uses whitespaces for separating code: space, new lines etc.
To push a number onto the stack we just write it out with whitespaces around.
```
1 2 3 // You have three numbers on the stack: 1, 2 and 3
-69   // Now you have four numbers: 1, 2, 3 and -69
```

## Arithmetics
Cont uses 2 values at the top of the stack to get parameters for an arithmetical operation.
For example:
If the stack looks like [1 2 3] and you perform an addition, the stack becomes [1 5].
And if the stack is [5 69 42] and you perform a subtraction, it becomes [5 27]
```
// Comments will show the stack state after every line
1   // [1]
2 3 // [1 2 3] 
+   // [1 5]
-   // [-4]
2 * // [-8]
```

There are also integer division and modulo operators, but to use them you will need to include `std.cn` or `core.cn`.
If you don't want to use these includes, you can use the `div` operator,
it pushes both the integer division result and the remainder onto the stack.
```
include std.cn

4 2 /               // [2]
7 3 %               // [2 1]
5 / // Divides 1 by 5: [2 0]
13 4 div            // [2 0 3 1]
// 3 is the 12 / 4 result and 1 is the remainder from 13 / 4
```

## Stack operations
Sometimes you need to change the element order on the stack. You can use the following stack operations to do that:
* dup: `a -> a a`
* drop: `a -> `
* swap: `a b -> b a`
* rot: `a b c -> c b a`
* over: `a b -> a b a`
```
1 2 // [1 2]
swap // [2 1]
dup // [2 1 1]
rot // [1 1 2]
over // [1 1 2 1]
+ // [1 1 3]
swap drop // [1 3]
swap - // [2] 
```

### A useful note
If you want to run the code yourself and maybe experiment with it,
you would probably want to see what values are on the stack.
You could use the `print` procedure from `std.cn` file for that.
It would look something like this.
```
include std.cn // Include the print procedure

1 2
swap print print
// You would see the following in your terminal:
// 1
// 2
```