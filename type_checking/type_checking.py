from parsing.op import *
from state import *
from .type_to_str import type_to_str

assert len(Operator) == 21, "Unimplemented operator in type_checking.py"
assert len(OpType) == 9, "Unimplemented type in type_checking.py"
assert len(BlockType) == 3, "Unimplemented block type in type_checking.py"

class ptr: pass

def check_stack(stack: list[type], expected: list[type]):
    if len(stack) < len(expected):
        print("Stack is too short")
        exit(1)
    for _ in range(len(expected)):
        got = stack.pop()
        exp = expected.pop()

        if got != exp and None not in (exp, got):
            print(f"Expected type {type_to_str(exp)}, got {type_to_str(got)}")
            exit(1)

def check_route_stack(stack1: list[type], stack2: list[type], error: str = "if-end"):
    if len(stack1) > len(stack2):
        print(f"Error: Stack has extra elements in different routes of {error}")
        print(f"Types: {', '.join(type_to_str(i) for i in stack1[len(stack2)-len(stack1):])}")
        exit(1)
    if len(stack1) < len(stack2):
        print(f"Error: Stack has not enought elements in different routes of {error}")
        print(f"Types: {', '.join(type_to_str(i) for i in stack2[len(stack1)-len(stack2):])}")
        exit(1)
    for i in range(len(stack1)):
        if stack1[i] != stack2[i] and None not in (stack1[i], stack2[i]):
            print(f"Different types in different routes of {error}")
            print(f"Element {len(stack1)-i}: {type_to_str(stack1[i])} instead of {type_to_str(stack2[i])}")
            exit(1)

def type_check(ops: list[Op]):
    stack: list[type] = [] 
    
    for op in ops:
        type_check_op(op, stack)

def type_check_op(op: Op, stack: list[type]):
    assert len(OpType) == 9, "Unimplemented type in type_check_op"

    if op.type == OpType.PUSH_INT:
        stack.append(int)
    elif op.type == OpType.PUSH_MEMORY:
        stack.append(ptr)
    elif op.type == OpType.IF:
        check_stack(stack, [int])
        State.route_stack.append(("if-end", stack.copy()))
    elif op.type == OpType.ELSE:
        original_stack = State.route_stack.pop()[1]
        State.route_stack.append(("if-else", stack.copy()))
        stack.clear()
        stack.extend(original_stack)
    elif op.type == OpType.ENDIF:
        route_stack = State.route_stack.pop()
        if route_stack[0] == "if-end":
            check_route_stack(stack, route_stack[1])
        else:
            check_route_stack(route_stack[1], stack, "if-else") 
    elif op.type == OpType.SYSCALL:
        check_stack(stack, [None] * (op.operand + 1))
        stack.append(None)
    elif op.type == OpType.OPERATOR:
        type_check_operator(op, stack)

def type_check_operator(op: Op, stack: list[Op]):
    assert len(Operator) == 21, "Unimplemented operator in type_check_operator"

    if op.operand in (Operator.ADD, Operator.SUB, Operator.MUL, Operator.DIV, Operator.GT,
                      Operator.LT, Operator.EQ, Operator.LE, Operator.GE, Operator.NE):
        check_stack(stack, [int, int])
        stack.append(int)
    elif op.operand == Operator.DUP:
        stack.append(stack[-1])
    elif op.operand == Operator.DROP:
        stack.pop()
    elif op.operand == Operator.SWAP:
        stack.append(stack.pop())
        stack.append(stack.pop())
    elif op.operand == Operator.ROT:
        stack.append(stack.pop())
        stack.append(stack.pop())
        stack.append(stack.pop())
    elif op.operand in (Operator.STORE,  Operator.STORE8):
        check_stack(stack, [int, ptr])
    elif op.operand in (Operator.LOAD,  Operator.LOAD8):
        check_stack(stack, [ptr])
        stack.append(int)
    elif op.operand == Operator.CAST_INT:
        stack.pop()
        stack.append(int)
    elif op.operand == Operator.CAST_PTR:
        stack.pop()
        stack.append(ptr)
    elif op.operand == Operator.PRINT:
        check_stack(stack, [int])
    else:
        assert False, f"Unimplemented operator in type_check_operator {op.operand.name}"
