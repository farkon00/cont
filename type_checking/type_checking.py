from parsing.op import *
from state import *
from .types import type_to_str
from .types import *

assert len(Operator) == 19, "Unimplemented operator in type_checking.py"
assert len(OpType) == 28, "Unimplemented type in type_checking.py"
assert len(BlockType) == 5, "Unimplemented block type in type_checking.py"

def check_stack(stack: list, expected: list, arg=0):
    if len(stack) < len(expected):
        State.throw_error("stack is too short")
    for i in range(len(expected)):
        got = stack.pop()
        exp = expected.pop()
        if got != exp and exp is not None and got is not None:
            State.throw_error(f"unexpected argument type", False)
            sys.stderr.write(f"\033[1;34mArgument {i+1+arg}\033[0m: {type_to_str(got)} instead of {type_to_str(exp)}\n")
            exit(1)

def check_route_stack(stack1: list, stack2: list, error: str = "in different routes of if-end"):
    if len(stack1) > len(stack2):
        State.throw_error(f"stack has extra elements {error}", False)
        sys.stderr.write(f"\033[1;34mTypes\033[0m: {', '.join(type_to_str(i) for i in stack1[len(stack2)-len(stack1):])}\n")
        exit(1)
    if len(stack1) < len(stack2):
        State.throw_error(f"stack has not enought elements {error}", False)
        sys.stderr.write(f"\033[1;34mTypes\033[0m: {', '.join(type_to_str(i) for i in stack2[len(stack1)-len(stack2):])}\n")
        exit(1)
    for i in range(len(stack1)):
        if stack1[i] != stack2[i] and stack1[i] is not None and stack2[i] is not None:
            State.throw_error(f"different types {error}", False)
            sys.stderr.write(f"\033[1;34mElement {len(stack1)-i}\033[0m: {type_to_str(stack1[i])} instead of {type_to_str(stack2[i])}\n")
            exit(1)

def type_check(ops: list[Op]):
    stack: list = [] 
    
    for index, op in enumerate(ops):
        new_op = type_check_op(op, stack)
        if new_op is not None:
            ops[index] = new_op

def type_check_op(op: Op, stack: list) -> Op | None:
    assert len(OpType) == 28, "Unimplemented type in type_check_op"

    State.loc = op.loc

    if op.type == OpType.PUSH_INT:
        stack.append(Int())
    elif op.type in (OpType.PUSH_MEMORY, OpType.PUSH_LOCAL_MEM):
        stack.append(Ptr())
    elif op.type == OpType.PUSH_VAR:
        stack.append(Ptr(State.variables[op.operand]))
    elif op.type == OpType.PUSH_LOCAL_VAR:
        assert State.current_proc is not None, "Probably bug in parsing with local and global variables"
        stack.append(Ptr(State.current_proc.variables[op.operand]))
    elif op.type == OpType.PUSH_STR:
        stack.append(Int())
        stack.append(Ptr())
    elif op.type == OpType.PUSH_NULL_STR:
        stack.append(Ptr())
    elif op.type == OpType.CAST:
        check_stack(stack, [None])
        stack.append(op.operand)
    elif op.type == OpType.IF:
        check_stack(stack, [Int()])
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
        check_stack(stack, [Int()])
        State.route_stack.append(("while", stack.copy()))
    elif op.type == OpType.ENDWHILE:
        check_stack(stack, [Int()])
        pre_while_stack = State.route_stack.pop()[1]
        check_route_stack(stack, pre_while_stack, "in different routes of while")
    elif op.type == OpType.BIND:
        if len(stack) < op.operand:
            State.throw_error("stack is too short for bind")
        State.bind_stack.extend(stack[-op.operand:])
        stack[-op.operand:] = []
    elif op.type == OpType.UNBIND:
        for _ in range(op.operand):
            State.bind_stack.pop() 
    elif op.type == OpType.PUSH_BIND_STACK:
        stack.append(State.bind_stack[op.operand])
    elif op.type == OpType.DEFPROC:
        State.route_stack.append(("proc", stack.copy()))
        stack.clear()
        stack.extend(op.operand.in_stack)
        State.current_proc = op.operand
    elif op.type == OpType.ENDPROC:
        check_route_stack(
            stack, State.get_proc_by_block(op.operand).out_stack, "in procedure definition"
        )
        stack.clear()
        stack.extend(State.route_stack.pop()[1])
        State.current_proc = None
    elif op.type == OpType.CALL:
        check_stack(stack, op.operand.in_stack.copy())
        stack.extend(op.operand.out_stack)
    elif op.type == OpType.TYPED_LOAD:
        check_stack(stack, [Ptr(op.operand)])
        stack.append(op.operand)
    elif op.type == OpType.TYPED_STORE:
        check_stack(stack, [op.operand, Ptr(op.operand)])
    elif op.type == OpType.PACK:
        struct = State.structures[op.operand]
        check_stack(stack, struct.fields_types.copy())
        stack.append(Ptr(struct))
    elif op.type in (OpType.PUSH_FIELD, ):
        if len(stack) < 1:
            State.throw_error("stack is too short")
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if not isinstance(ptr.typ, Struct):
            State.throw_error(f"cant access field of non-struct : {type_to_str(ptr.typ)}")
        if op.operand not in (*ptr.typ.fields, *ptr.typ.methods):
            State.throw_error(f"field {op.operand} not found on {type_to_str(ptr.typ)}")
        if op.operand in ptr.typ.fields:
            offset = 0
            for i, j in ptr.typ.fields.items():
                if i == op.operand:
                    break
                offset += sizeof(j)
            stack.append(ptr.typ.fields[op.operand])
            return Op(OpType.PUSH_FIELD, offset, op.loc)
        else:
            method = ptr.typ.methods[op.operand]
            check_stack(stack + [ptr], method.in_stack.copy())
            stack.extend(method.out_stack)
            return Op(OpType.CALL, method, op.loc)
    elif op.type == OpType.PUSH_FIELD_PTR:
        if len(stack) < 1:
            State.throw_error("stack is too short")
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if not isinstance(ptr.typ, Struct):
            State.throw_error(f"cant access field of non-struct : {type_to_str(ptr.typ)}")
        if op.operand not in ptr.typ.fields:
            State.throw_error(f"field {op.operand} not found on {type_to_str(ptr.typ)}")
        offset = 0
        for i, j in ptr.typ.fields.items():
            if i == op.operand:
                break
            offset += sizeof(j)
        stack.append(Ptr(ptr.typ.fields[op.operand]))
        return Op(OpType.PUSH_FIELD_PTR, offset, op.loc)
    elif op.type == OpType.SYSCALL:
        check_stack(stack, [None] * (op.operand + 1))
        stack.append(None)
    elif op.type == OpType.OPERATOR:
        return type_check_operator(op, stack)

    return None

def type_check_operator(op: Op, stack: list) -> Op | None:
    assert len(Operator) == 19, "Unimplemented operator in type_check_operator"

    if op.operand in (Operator.ADD, Operator.SUB, Operator.MUL, Operator.GT, Operator.LT,
                      Operator.EQ, Operator.LE, Operator.GE, Operator.NE):
        check_stack(stack, [Int(), Int()])
        stack.append(Int())
    elif op.operand == Operator.DIV:
        check_stack(stack, [Int(), Int()])
        stack.append(Int())
        stack.append(Int())
    elif op.operand == Operator.DUP:
        if len(stack) < 1:
            State.throw_error("stack is too short")
        stack.append(stack[-1])
    elif op.operand == Operator.DROP:
        check_stack(stack, [None])
    elif op.operand == Operator.SWAP:
        if len(stack) < 2:
            State.throw_error("stack is too short")
        stack[-2], stack[-1] = stack[-1], stack[-2]
    elif op.operand == Operator.ROT:
        if len(stack) < 3:
            State.throw_error("stack is too short")
        stack[-3], stack[-2], stack[-1] = stack[-1], stack[-2], stack[-3]
    elif op.operand == Operator.STORE:
        if len(stack) < 1:
            State.throw_error("stack is too short")
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if ptr.typ is None:
            check_stack(stack, [Int()], arg=1)
        elif isinstance(ptr.typ, Struct):
            check_stack(stack, [Ptr(ptr.typ)], arg=1)
            return Op(OpType.MOVE_STRUCT, sizeof(ptr.typ), State.loc)
        else:
            check_stack(stack, [ptr.typ], arg=1)
    elif op.operand == Operator.STORE8:
        check_stack(stack, [Int(), Ptr()])
    elif op.operand == Operator.LOAD:
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if ptr.typ is None:
            stack.append(Int())
        elif isinstance(ptr.typ, Struct):
            if not ptr.typ.is_unpackable:
                State.throw_error(f"cant unpack {type_to_str(ptr.typ)}")
            stack.extend(ptr.typ.fields_types)
            return Op(OpType.UNPACK, sizeof(ptr.typ))
        else:
            stack.append(ptr.typ)
    elif op.operand == Operator.LOAD8:
        check_stack(stack, [Ptr()])
        stack.append(Int())
    elif op.operand == Operator.PRINT:
        check_stack(stack, [Int()])
    else:
        assert False, f"Unimplemented operator in type_check_operator {op.operand.name}"

    return None