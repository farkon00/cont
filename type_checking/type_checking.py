from parsing.op import *
from state import *
from .type_to_str import type_to_str

assert len(Operator) == 21, "Unimplemented operator in type_checking.py"
assert len(OpType) == 9, "Unimplemented type in type_checking.py"
assert len(BlockType) == 3, "Unimplemented block type in type_checking.py"

class ptr: pass

def check_stack(stack: list[Op], expected: list[type]):
    if len(stack) < len(expected):
        print("Stack is too short")
        exit(1)
    for _ in expected:
        got = stack.pop()
        exp = expected.pop()
        if got != exp:
            print(f"Expected type {type_to_str(exp)}, got {type_to_str(got)}")
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
