from typing import List, Dict, Union, Iterable

from parsing.op import *
from state import *
from .types import type_to_str
from .types import *

assert len(Operator) == 20, "Unimplemented operator in type_checking.py"
assert len(OpType) == 40, "Unimplemented type in type_checking.py"
assert len(BlockType) == 6, "Unimplemented block type in type_checking.py"


def check_stack(stack: List[Type], expected: List[Type], arg=0):
    if len(stack) < len(expected):
        State.throw_error("stack is too short")
    for i in range(len(expected)):
        got = stack.pop()
        exp = expected.pop()
        if got != exp and exp is not None and got is not None:
            State.throw_error(f"unexpected argument type", False)
            sys.stderr.write(
                f"\033[1;34mArgument {i+1+arg}\033[0m: {type_to_str(got)} instead of {type_to_str(exp)}\n"
            )
            exit(1)


def check_route_stack(
    stack1: List[Type], stack2: List[Type], error: str = "in different routes of if-end"
):
    if len(stack1) > len(stack2):
        State.throw_error(f"stack has extra elements {error}", False)
        sys.stderr.write(
            f"\033[1;34mTypes\033[0m: {', '.join(type_to_str(i) for i in stack1[len(stack2)-len(stack1):])}\n"
        )
        exit(1)
    if len(stack1) < len(stack2):
        State.throw_error(f"stack has not enought elements {error}", False)
        sys.stderr.write(
            f"\033[1;34mTypes\033[0m: {', '.join(type_to_str(i) for i in stack2[len(stack1)-len(stack2):])}\n"
        )
        exit(1)
    for i in range(len(stack1)):
        if (
            not check_varient(stack1[i], stack2[i])
            and stack1[i] is not None
            and stack2[i] is not None
        ):
            State.throw_error(f"different types {error}", False)
            sys.stderr.write(
                f"\033[1;34mElement {len(stack1)-i}\033[0m: {type_to_str(stack1[i])} instead of {type_to_str(stack2[i])}\n"
            )
            exit(1)

        stack1[i] = down_cast(stack1[i], stack2[i])


def type_check(ops: List[Op], is_main: bool = False):
    stack: list = []

    if is_main and State.config.struct_malloc[1]:
        State.loc = ""
        if "malloc" not in State.procs:
            if State.config.struct_malloc[0]:
                State.throw_error(
                    "Malloc procedure not found while struct_malloc is enabled"
                )
            else:
                State.config.config["struct_malloc"] = (
                    State.config.struct_malloc[0],
                    False,
                )
        else:
            proc = State.procs["malloc"]
            if proc.in_stack != [Int()]:
                if State.config.struct_malloc[0]:
                    State.throw_error(
                        "Malloc must take one integer, disable struct_malloc if you don't want language to use malloc"
                    )
                else:
                    State.config.config["struct_malloc"] = (
                        State.config.struct_malloc[0],
                        False,
                    )
            if proc.out_stack != [Ptr()]:
                if State.config.struct_malloc[0]:
                    State.throw_error(
                        "Malloc must return one pointer, disable struct_malloc if you don't want language to use malloc"
                    )
                else:
                    State.config.config["struct_malloc"] = (
                        State.config.struct_malloc[0],
                        False,
                    )

        if State.config.struct_malloc[1]:
            State.add_proc_use(proc)

    if is_main and len(State.runtimed_types):
        State.loc = ""
        for struct in State.TYPE_STRUCTS:
            if struct not in State.structures:
                State.throw_error(
                    f"If types in runtime are used type.cn must be included from std. Structure {struct} not found."
                )

    index = 0
    while index < len(ops):
        op = ops[index]
        new_op = type_check_op(op, stack)
        if isinstance(new_op, Iterable):
            ops[index : index + 1] = new_op
            index += len(new_op) - 1
        elif new_op is not None:
            ops[index] = new_op

        index += 1

    return stack


def process_for_in(op: Op, stack: List[Type], iter_stack: list) -> list:
    type_ = iter_stack[0]
    check_stack(iter_stack, [Ptr(Array())])
    type_ = type_.typ
    State.ops_by_ips[op.operand[0].end].operand = (*op.operand[:2], type_)
    if type_.len == 0:
        return []
    State.route_stack.append(("for", stack.copy()))
    State.bind_stack.extend((Int(), type_.typ))
    if State.config.re_IOR:
        State.locs_to_include.append(op.loc)
    op.operand[0].type = BlockType.WHILE
    return [
        Op(OpType.PUSH_INT, 0, loc=op.loc),
        Op(OpType.PUSH_INT, 1, loc=op.loc),
        Op(OpType.WHILE, op.operand[0], loc=op.loc),
        Op(OpType.OPERATOR, Operator.DUP, loc=op.loc),
        *op.operand[2],
        Op(
            OpType.INDEX,
            (sizeof(type_.typ), type_.len),
            loc_id=len(State.locs_to_include) - 1,
            loc=op.loc,
        ),
        Op(OpType.BIND, 2, loc=op.loc),
    ]


def process_for_until(op: Op, stack: List[Type], iter_stack: list) -> list:
    check_stack(iter_stack, [Ptr()])
    State.route_stack.append(("for", stack.copy()))
    State.bind_stack.extend((Ptr(), Int()))
    op.operand[0].type = BlockType.WHILE

    if State.config.re_NPD:
        State.locs_to_include.append(op.loc)

    return [
        *op.operand[2],
        Op(OpType.OPERATOR, Operator.DUP, loc=op.loc),
        Op(
            OpType.OPERATOR,
            Operator.LOAD8,
            loc=op.loc,
            loc_id=len(State.locs_to_include) - 1,
        ),
        Op(OpType.OPERATOR, Operator.DUP, loc=op.loc),
        Op(OpType.PUSH_INT, 0, loc=op.loc),
        Op(OpType.OPERATOR, Operator.NE, loc=op.loc),
        Op(OpType.WHILE, op.operand[0], loc=op.loc),
        Op(OpType.BIND, 2, loc=op.loc),
    ]


def match_type_var(typ: Optional[Type], actual: Optional[Type]) -> Dict[int, Type]:
    if typ is None or actual is None:
        return {}
    if isinstance(typ, VarType):
        return {id(typ): actual}
    if isinstance(typ, Ptr) and isinstance(actual, Ptr):
        return match_type_var(typ.typ, actual.typ)
    if isinstance(typ, Array) and isinstance(actual, Array):
        return match_type_var(typ.typ, actual.typ)
    return {}


def get_var_type_values(types: List[Type], stack: List[Type]) -> Dict[int, Type]:
    var_types: Dict[int, Type] = {}
    if len(types) > len(stack):
        State.throw_error("Not enough elements on the stack")
    for typ, actual in zip(types, stack):
        var_types = {**match_type_var(typ, actual), **var_types}
    return var_types


def get_concrete_type(typ: Type, var_types: Dict[int, Type]) -> Type:
    if isinstance(typ, VarType):
        if id(typ) not in var_types:
            State.throw_error(f'Cannot obtain value for type varaible "{typ.name}"')
        return var_types[id(typ)]
    if isinstance(typ, Ptr):
        return Ptr(get_concrete_type(typ.typ, var_types))  # type: ignore
    if isinstance(typ, Array):
        return Array(typ.len, get_concrete_type(typ.typ, var_types))  # type: ignore
    return typ


def process_call(op: Op, stack: List[Type]) -> None:
    in_types: List[object] = []
    out_types: List[object] = []
    var_types = get_var_type_values(
        op.operand.in_stack, stack[-len(op.operand.in_stack) :]
    )
    for typ in op.operand.in_stack:
        in_types.append(get_concrete_type(typ, var_types))
    for typ in op.operand.out_stack:
        out_types.append(get_concrete_type(typ, var_types))
    check_stack(stack, in_types)
    stack.extend(out_types)


def type_check_op(op: Op, stack: List[Type]) -> Optional[Union[Op, List[Op]]]:
    assert len(OpType) == 40, "Unimplemented type in type_check_op"

    State.loc = op.loc

    if not op.compiled:
        return None

    if op.type == OpType.PUSH_INT:
        stack.append(Int())
    elif op.type in (OpType.PUSH_MEMORY, OpType.PUSH_LOCAL_MEM):
        stack.append(Ptr())
    elif op.type == OpType.PUSH_VAR:
        if must_ptr(State.variables[op.operand]):
            stack.append(Ptr(State.variables[op.operand]))
            return Op(OpType.PUSH_VAR_PTR, op.operand, loc=op.loc)
        else:
            stack.append(State.variables[op.operand])
    elif op.type == OpType.PUSH_VAR_PTR:
        if must_ptr(State.variables[op.operand]):
            State.throw_error(
                "variable is automatically a pointer, cannot push a pointer excplicitly"
            )
        stack.append(Ptr(State.variables[op.operand]))
    elif op.type == OpType.PUSH_LOCAL_VAR:
        assert (
            State.current_proc is not None
        ), "Probably bug in parsing with local and global variables"
        if must_ptr(State.current_proc.variables[op.operand]):
            stack.append(Ptr(State.current_proc.variables[op.operand]))
            return Op(OpType.PUSH_LOCAL_VAR_PTR, op.operand, loc=op.loc)
        else:
            stack.append(State.current_proc.variables[op.operand])
    elif op.type == OpType.PUSH_LOCAL_VAR_PTR:
        assert (
            State.current_proc is not None
        ), "Probably bug in parsing with local and global variables"
        if must_ptr(State.current_proc.variables[op.operand]):
            State.throw_error(
                "variable is automatically a pointer, cannot push a pointer excplicitly"
            )

        stack.append(Ptr(State.current_proc.variables[op.operand]))
    elif op.type == OpType.PUSH_STR:
        stack.append(Int())
        stack.append(Ptr())
    elif op.type == OpType.PUSH_NULL_STR:
        stack.append(Ptr())
    elif op.type == OpType.PUSH_PROC:
        stack.append(Addr())
    elif op.type == OpType.CAST:
        check_stack(stack, [None])
        stack.append(op.operand)
    elif op.type == OpType.UPCAST:
        if len(stack) < 1:
            State.throw_error("stack is too short")
        struct = stack[-1]
        check_stack(stack, [Ptr()])
        if not isinstance(struct.typ, Struct):
            State.throw_error("can't upcast non-struct")

        struct = struct.typ
        if op.operand != struct:
            State.throw_error(
                f"can't upcast {type_to_str(struct)} to {type_to_str(op.operand)}"
            )

        check_stack(stack, op.operand.fields_types[len(struct.fields_types) :])

        stack.append(Ptr(op.operand))

        return Op(
            OpType.UPCAST,
            (
                sizeof(op.operand),
                len(op.operand.fields_types) - len(struct.fields_types),
                sizeof(struct),
            ),
            op.loc,
        )
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
    elif op.type == OpType.FOR:
        iter_stack = type_check(op.operand[2])
        if len(iter_stack) != 1:
            State.throw_error("iterable expression should return one value")
        if op.operand[1] == "in":
            return process_for_in(op, stack, iter_stack)
        elif op.operand[1] == "until":
            return process_for_until(op, stack, iter_stack)
        else:
            assert False, "Unreachable"
    elif op.type == OpType.ENDFOR:
        State.bind_stack.pop()
        State.bind_stack.pop()
        if op.operand[1] == "in":
            if op.operand[2].len == 0:
                return []
            pre_for_stack = State.route_stack.pop()[1]
            check_route_stack(stack, pre_for_stack, "in different routes of for")
            return [
                Op(OpType.PUSH_BIND_STACK, len(State.bind_stack), loc=op.loc),
                Op(OpType.PUSH_INT, 1, loc=op.loc),
                Op(OpType.OPERATOR, Operator.ADD, loc=op.loc),
                Op(OpType.OPERATOR, Operator.DUP, loc=op.loc),
                Op(OpType.PUSH_INT, op.operand[2].len, loc=op.loc),
                Op(OpType.OPERATOR, Operator.LT, loc=op.loc),
                Op(OpType.UNBIND, 2, loc=op.loc),
                Op(OpType.ENDWHILE, op.operand[0], loc=op.loc),
                Op(OpType.OPERATOR, Operator.DROP, loc=op.loc),
            ]
        elif op.operand[1] == "until":
            pre_for_stack = State.route_stack.pop()[1]
            check_route_stack(stack, pre_for_stack, "in different routes of for")

            if State.config.re_NPD:
                State.locs_to_include.append(op.loc)

            return [
                Op(OpType.PUSH_BIND_STACK, len(State.bind_stack), loc=op.loc),
                Op(OpType.PUSH_INT, 1, loc=op.loc),
                Op(OpType.OPERATOR, Operator.ADD, loc=op.loc),
                Op(OpType.OPERATOR, Operator.DUP, loc=op.loc),
                Op(
                    OpType.OPERATOR,
                    Operator.LOAD8,
                    loc=op.loc,
                    loc_id=len(State.locs_to_include) - 1,
                ),
                Op(OpType.OPERATOR, Operator.DUP, loc=op.loc),
                Op(OpType.PUSH_INT, 0, loc=op.loc),
                Op(OpType.OPERATOR, Operator.NE, loc=op.loc),
                Op(OpType.UNBIND, 2, loc=op.loc),
                Op(OpType.ENDWHILE, op.operand[0], loc=op.loc),
            ]
    elif op.type == OpType.BIND:
        if len(stack) < op.operand:
            State.throw_error("stack is too short for bind")
        State.bind_stack.extend(stack[-op.operand :])
        stack[-op.operand :] = []
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
            stack,
            State.get_proc_by_block(op.operand).out_stack,
            "in procedure definition",
        )
        stack.clear()
        stack.extend(State.route_stack.pop()[1])
        State.current_proc = None
    elif op.type == OpType.CALL:
        process_call(op, stack)
    elif op.type == OpType.TYPED_LOAD:
        check_stack(stack, [Ptr(op.operand)])
        stack.append(op.operand)
    elif op.type == OpType.PACK:
        struct = State.structures[op.operand]
        if "__init__" in struct.methods:
            args = struct.methods["__init__"].in_stack.copy()[:-1]
            State.add_proc_use(struct.methods["__init__"])
        else:
            args = struct.fields_types.copy()
            for i, j in enumerate(struct.defaults):
                del args[j - i]
        check_stack(stack, args)
        stack.append(Ptr(struct))
    elif op.type == OpType.PUSH_FIELD:
        if len(stack) < 1:
            State.throw_error("stack is too short")
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if not isinstance(ptr.typ, Struct):
            State.throw_error(
                f"cant access field of non-struct : {type_to_str(ptr.typ)}"
            )
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
            State.add_proc_use(method)
            check_stack(stack, method.in_stack.copy()[:-1])
            stack.extend(method.out_stack)
            return Op(OpType.CALL, method, op.loc)
    elif op.type == OpType.PUSH_FIELD_PTR:
        if len(stack) < 1:
            State.throw_error("stack is too short")
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if not isinstance(ptr.typ, Struct):
            State.throw_error(
                f"cant access field of non-struct : {type_to_str(ptr.typ)}"
            )
        if op.operand not in ptr.typ.fields:
            State.throw_error(f"field {op.operand} not found on {type_to_str(ptr.typ)}")
        offset = 0
        for i, j in ptr.typ.fields.items():
            if i == op.operand:
                break
            offset += sizeof(j)
        stack.append(Ptr(ptr.typ.fields[op.operand]))
        return Op(OpType.PUSH_FIELD_PTR, offset, op.loc)
    elif op.type == OpType.CALL_LIKE:
        check_stack(stack, [*op.operand.in_stack, Addr()])
        stack.extend(op.operand.out_stack)
    elif op.type in (OpType.INDEX, OpType.INDEX_PTR):
        if len(stack) < 1:
            State.throw_error("stack is too short")
        arr = stack[-1]
        if isinstance(arr, Ptr):
            if isinstance(arr.typ, Struct):
                if f"__{op.type.name.lower()}__" in arr.typ.methods:
                    proc = arr.typ.methods[f"__{op.type.name.lower()}__"]
                    State.add_proc_use(proc)
                    check_stack(stack, proc.in_stack.copy())
                    stack.extend(proc.out_stack)
                    return [Op(OpType.CALL, proc, op.loc)]
                stack.pop()
        check_stack(stack, [Int(), Ptr(Array())])
        stack.append(arr.typ.typ if op.type == OpType.INDEX else Ptr(arr.typ.typ))
        if State.config.re_IOR:
            State.locs_to_include.append(op.loc)
        return Op(
            op.type,
            (sizeof(arr.typ.typ), arr.typ.len),
            loc=op.loc,
            loc_id=len(State.locs_to_include) - 1,
        )
    elif op.type == OpType.SIZEOF:
        if len(stack) < 1:
            State.throw_error("stack is too short")
        _type = stack.pop()
        stack.append(Int())
        for i in range(op.operand):
            if not hasattr(_type, "typ"):
                State.throw_error(f"{type_to_str(_type)} has no type")
            if _type.typ is None:
                State.throw_error(f"{type_to_str(_type)} has no type")
            _type = _type.typ

        return Op(OpType.PUSH_INT, sizeof(_type))
    elif op.type == OpType.PUSH_TYPE:
        if isinstance(op.operand, (Int, Addr)):
            stack.append(Ptr(State.structures["Type"]))
        elif isinstance(op.operand, Ptr):
            stack.append(Ptr(State.structures["PtrType"]))
        elif isinstance(op.operand, Array):
            stack.append(Ptr(State.structures["ArrayType"]))
    elif op.type == OpType.SYSCALL:
        check_stack(stack, [None] * (op.operand + 1))
        stack.append(None)
    elif op.type == OpType.OPERATOR:
        return type_check_operator(op, stack)
    elif op.type in (OpType.AUTO_INIT, OpType.ASM):
        pass  # This operations are generation thing
    else:
        assert False, f"unknown op type in type_check_op: {op.type.name}"

    return None


def type_check_operator(op: Op, stack: List[Type]) -> Optional[Union[Op, List[Op]]]:
    assert len(Operator) == 20, "Unimplemented operator in type_check_operator"

    if op.operand in (
        Operator.ADD,
        Operator.SUB,
        Operator.MUL,
        Operator.GT,
        Operator.LT,
        Operator.EQ,
        Operator.LE,
        Operator.GE,
        Operator.NE,
    ):
        if len(stack) < 2:
            State.throw_error("stack is too short")
        type2 = stack.pop()
        type1 = stack.pop()
        if type1 == Int() and type2 == Int():
            stack.append(Int())
        elif type1 == Ptr() and type2 == Ptr():
            if isinstance(type1.typ, Struct):
                if type1.typ != type2.typ and type2.typ != type1.typ:
                    State.throw_error(
                        f"cant perform operation on different types: {type_to_str(type1.typ)} and {type_to_str(type2.typ)}"
                    )
                if f"__{op.operand.name.lower()}__" not in type1.typ.methods:
                    State.throw_error(
                        f"method __{op.operand.name.lower()}__ not found on {type_to_str(type1.typ)}"
                    )
                method = type1.typ.methods[f"__{op.operand.name.lower()}__"]
                stack.extend(method.out_stack)
                State.add_proc_use(method)
                return [
                    Op(OpType.OPERATOR, Operator.SWAP, loc=op.loc),
                    Op(OpType.CALL, method, loc=op.loc),
                ]
        else:
            State.throw_error(f"incompatible types for {op.operand.name.lower()}")
    elif op.operand == Operator.DIV:
        if len(stack) < 2:
            State.throw_error("stack is too short")
        type2 = stack.pop()
        type1 = stack.pop()
        if type1 == Int() and type2 == Int():
            stack.extend([Int(), Int()])
        elif type1 == Ptr() and type2 == Ptr():
            if isinstance(type1.typ, Struct):
                if type1.typ != type2.typ:
                    State.throw_error(
                        f"cant add different types: {type_to_str(type1.typ)} and {type_to_str(type2.typ)}"
                    )
                if f"__div__" not in type1.typ.methods:
                    State.throw_error(
                        f"method __div__ not found on {type_to_str(type1.typ)}"
                    )
                method = type1.typ.methods[f"__div__"]
                stack.extend(method.out_stack)
                State.add_proc_use(method)
                return [
                    Op(OpType.OPERATOR, Operator.SWAP, loc=op.loc),
                    Op(OpType.CALL, method, loc=op.loc),
                ]
        else:
            State.throw_error(f"incompatible types for div")
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
    elif op.operand == Operator.OVER:
        if len(stack) < 2:
            State.throw_error("stack is too short")
        stack.append(stack[-2])
    elif op.operand in (Operator.STORE, Operator.STRONG_STORE):
        if len(stack) < 1:
            State.throw_error("stack is too short")
        State.locs_to_include.append(op.loc)
        op.loc_id = len(State.locs_to_include) - 1
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if ptr.typ is None:
            check_stack(stack, [Int()], arg=1)
        elif isinstance(ptr.typ, Struct) and op.operand == Operator.STORE:
            check_stack(stack, [Ptr(ptr.typ)], arg=1)
            return Op(OpType.MOVE_STRUCT, sizeof(ptr.typ), State.loc)
        else:
            check_stack(stack, [ptr.typ], arg=1)
        if op.operand == Operator.STRONG_STORE:
            return Op(OpType.OPERATOR, Operator.STORE, op.loc)
    elif op.operand == Operator.STORE8:
        State.locs_to_include.append(op.loc)
        op.loc_id = len(State.locs_to_include) - 1
        check_stack(stack, [Int(), Ptr()])
    elif op.operand == Operator.LOAD:
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        State.locs_to_include.append(op.loc)
        op.loc_id = len(State.locs_to_include) - 1
        if ptr.typ is None:
            stack.append(Int())
        elif ptr.typ == Array():
            State.throw_error("cant unpack array to stack")
        elif isinstance(ptr.typ, Struct):
            if not ptr.typ.is_unpackable:
                State.throw_error(f"cant unpack {type_to_str(ptr.typ)}")
            stack.extend(ptr.typ.fields_types)
            return Op(OpType.UNPACK, sizeof(ptr.typ))
        else:
            stack.append(ptr.typ)
    elif op.operand == Operator.LOAD8:
        State.locs_to_include.append(op.loc)
        op.loc_id = len(State.locs_to_include) - 1
        check_stack(stack, [Ptr()])
        stack.append(Int())
    else:
        assert False, f"Unimplemented operator in type_check_operator {op.operand.name}"

    return None
