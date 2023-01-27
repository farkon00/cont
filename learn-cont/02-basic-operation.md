# Basic operations

# Stack

Cont is stack-based language, which means to perform actions we push parameters onto stack and pop them for operations.
You can read more about stack data structure [here](https://en.wikipedia.org/wiki/Stack_(abstract_data_type)).

The cont is in most cases whitespace significant, which means it is separating code by spaces, newlines etc.
To push a number onto the stack we just write it down.
```
1 2 3 // You have three numbers on the stack: 1, 2 and 3
-69   // Now you have four numbers: 1, 2, 3 and -69
```

# Arithmetics
Cont uses 2 top values on the stack to get the parameters for the aithmetic operation.
For example:
If the stack looks like [1 2 3] and you perform an addition, the stack would become [1 5].
And if the stack is [5 69 42] and you perform a subtraction, it would become [5 27]
```
// Comments will show the stack state after every line
1   // [1]
2 3 // [1 2 3] 
+   // [1 5]
-   // [-4]
2 * // [-8]
```

There is also integer division and modulo operators, but to use them you will need to include either `std.cn` or `core.cn`.
If you don't want to use this includes, you can use `div` operator, it pushes both integer division result and remainder
onto the stack.
```
include std.cn

4 2 /               // [2]
7 3 %               // [2 1]
5 / // Divides 1 by 5: [2 0]
13 4 div            // [2 0 3 1]
// 3 is the 12 / 4 result and 1 is the remainder from 13 / 4
```

# Stack operations
Sometimes you need to change order of the elemnts on the stack. You can use following stack operation to do that:
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

# Useful note
If you want to test the code out and maybe experement with it you would probably want to see what values are on the stack.
You could use the `print` procedure from `std.cn` file. It would look something like this.
```
include std.cn // Include the print procedure

1 2
swap print print
// You would see the following in your terminal:
// 1
// 2
```