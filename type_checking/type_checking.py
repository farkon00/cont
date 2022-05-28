from parsing.op import *
from state import *
from .type_to_str import type_to_str

assert len(Operator) == 19, "Unimplemented operator in type_checking.py"
assert len(OpType) == 9, "Unimplemented type in type_checking.py"
assert len(BlockType) == 3, "Unimplemented block type in type_checking.py"

class ptr: pass

def check_stack(stack: list[Op], expected: list[type]):
    if len(stack) < len(expected):
        print("Stack too short")
    for i in range(len(expected)):
        got = stack.pop()
        exp = expected.pop()
        if got != exp:
            print(f"Expected type {type_to_str(exp)}, got {type_to_str(got)}")

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
    assert len(Operator) == 19, "Unimplemented operator in type_check_operator"

    if op.operand in (Operator.ADD, Operator.SUB, Operator.MUL, Operator.DIV):
        check_stack(stack, [int, int])
        stack.append(int)
    else:
        assert False, f"Unimplemented operator in type_check_operator {op.operand.name}"
