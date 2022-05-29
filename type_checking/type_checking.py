from parsing.op import *
from state import *
from .type_to_str import type_to_str

assert len(Operator) == 21, "Unimplemented operator in type_checking.py"
assert len(OpType) == 12, "Unimplemented type in type_checking.py"
assert len(BlockType) == 4, "Unimplemented block type in type_checking.py"

class ptr: pass

def check_stack(stack: list[type], expected: list[type]):
    if len(stack) < len(expected):
        State.throw_error("Stack is too short")
    for _ in range(len(expected)):
        got = stack.pop()
        exp = expected.pop()

        if got != exp and object not in (exp, got):
            State.throw_error(f"Expected type {type_to_str(exp)}, got {type_to_str(got)}")

def check_route_stack(stack1: list[type], stack2: list[type], error: str = "in different routes of if-end"):
    if len(stack1) > len(stack2):
        State.throw_error(f"Error: Stack has extra elements {error}", False)
        print(f"\033[1;34mTypes\033[0m: {', '.join(type_to_str(i) for i in stack1[len(stack2)-len(stack1):])}")
        exit(1)
    if len(stack1) < len(stack2):
        State.throw_error(f"Error: Stack has not enought elements {error}", False)
        print(f"\033[1;34mTypes\033[0m: {', '.join(type_to_str(i) for i in stack2[len(stack1)-len(stack2):])}")
        exit(1)
    for i in range(len(stack1)):
        if stack1[i] != stack2[i] and object not in (stack1[i], stack2[i]):
            State.throw_error(f"Different types {error}", False)
            print(f"\033[1;34mElement {len(stack1)-i}\033[0m: {type_to_str(stack1[i])} instead of {type_to_str(stack2[i])}")
            exit(1)

def type_check(ops: list[Op]):
    stack: list[type] = [] 
    
    for op in ops:
        type_check_op(op, stack)

def type_check_op(op: Op, stack: list[type]):
    assert len(OpType) == 12, "Unimplemented type in type_check_op"

    State.loc = op.loc

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
            check_route_stack(stack, route_stack[1], "in different routes of if-else") 
    elif op.type == OpType.WHILE:
        check_stack(stack, [int])
        State.route_stack.append(("while", stack.copy()))
    elif op.type == OpType.ENDWHILE:
        check_stack(stack, [int])
        pre_while_stack = State.route_stack.pop()[1]
        check_route_stack(stack, pre_while_stack, "in different routes of while")
    elif op.type == OpType.DEFPROC:
        State.route_stack.append(("proc", stack.copy()))
        stack.clear()
        stack.extend(State.procs[op.operand].in_stack)
    elif op.type == OpType.ENDPROC:
        check_route_stack(
            stack, State.get_proc_by_block(op.operand).out_stack, "in procedure definition"
        )
        stack.clear()
        stack.extend(State.route_stack.pop()[1])
    elif op.type == OpType.CALL:
        check_stack(stack, op.operand.in_stack.copy())
        stack.extend(op.operand.out_stack)
    elif op.type == OpType.SYSCALL:
        check_stack(stack, [object] * (op.operand + 1))
        stack.append(object)
    elif op.type == OpType.OPERATOR:
        type_check_operator(op, stack)

def type_check_operator(op: Op, stack: list[type]):
    assert len(Operator) == 21, "Unimplemented operator in type_check_operator"

    if op.operand in (Operator.ADD, Operator.SUB, Operator.MUL, Operator.DIV, Operator.GT,
                      Operator.LT, Operator.EQ, Operator.LE, Operator.GE, Operator.NE):
        check_stack(stack, [int, int])
        stack.append(int)
    elif op.operand == Operator.DUP:
        if len(stack) < 1:
            State.throw_error("Stack is too short")
        stack.append(stack[-1])
    elif op.operand == Operator.DROP:
        check_stack(stack, [object])
    elif op.operand == Operator.SWAP:
        if len(stack) < 2:
            State.throw_error("Stack is too short")
        stack.append(stack.pop(0))
        stack.append(stack.pop(1))
    elif op.operand == Operator.ROT:
        if len(stack) < 3:
            State.throw_error("Stack is too short")
        stack.append(stack.pop())
        stack.append(stack.pop())
        stack.append(stack.pop())
    elif op.operand in (Operator.STORE,  Operator.STORE8):
        check_stack(stack, [int, ptr])
    elif op.operand in (Operator.LOAD,  Operator.LOAD8):
        check_stack(stack, [ptr])
        stack.append(int)
    elif op.operand == Operator.CAST_INT:
        check_stack(stack, [object])
        stack.append(int)
    elif op.operand == Operator.CAST_PTR:
        check_stack(stack, [object])
        stack.append(ptr)
    elif op.operand == Operator.PRINT:
        check_stack(stack, [int])
    else:
        assert False, f"Unimplemented operator in type_check_operator {op.operand.name}"
