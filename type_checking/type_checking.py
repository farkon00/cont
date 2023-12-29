from typing import List, Dict, Union, Iterable

from parsing.op import *
from state import *
from .types import type_to_str
from .types import *

assert len(Operator) == 20, "Unimplemented operator in type_checking.py"
assert len(OpType) == 40, "Unimplemented type in type_checking.py"
assert len(BlockType) == 6, "Unimplemented block type in type_checking.py"


def check_stack(stack: List[Type], expected: List[Type], arg=0):
    """
    Checks whether the types at the top of the `stack` match those
    in `expected`. If they are not throws an appropriate error.
    
    The `arg` is the amount of types before the `expected`. This will only be
    used for error messages.

    Examples:
    * [int, ptr], [int, *int] -> does not throw
    * [int, int, ptr], [int, *int] -> does not throw
    * [ptr], [int, *int] -> error: the stack is too short
    * [ptr, int, int], [int, *int] -> error: error: type mismatch
    """
    assert len(stack) >= len(expected), "stack is too short"
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
    stack1: List[Type], stack2: List[Type], can_collapse_stack: bool = True,
    error: str = "in different routes of if-end"
):
    """
    Checks whether the stacks can be collapsed into one stack(using types.down_stack).

    If the function `can_collapse_stack` it means, that
    the checking becomes looser and `stack1` can be modified with types, that
    will be on the stack after the branches' control flow joins. Otherwise a simple
    equals check will be performed for every type.

    The error indicates the type of routes, which will be used for error messages.
    """
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
        if can_collapse_stack:
            typ, is_succ = down_cast(stack1[i], stack2[i])
            if not is_succ:
                State.throw_error(f"different types {error}", False)
                sys.stderr.write(
                    f"\033[1;34mElement {len(stack1)-i}\033[0m: {type_to_str(stack1[i])} instead of {type_to_str(stack2[i])}\n"
                )
                exit(1)
            stack1[i] = typ
        else:
            if stack1[i] != stack2[i] and stack1[i] is not None and stack2[i] is not None:
                State.throw_error(f"different types {error}", False)
                sys.stderr.write(
                    f"\033[1;34mElement {len(stack1)-i}\033[0m: {type_to_str(stack1[i])} instead of {type_to_str(stack2[i])}\n"
                )
                exit(1)


def type_check(ops: List[Op], is_main: bool = False) -> list:
    """
    Type checks the list of operations `op`. Returns the stack at the end of execution.
    Might modify the operations list because of desugaring or adding new information,
    which can only be added if the types are known. 

    The function should be called with is_main set to True only one time per compilation.
    """
    stack: list = []

    if is_main and State.config.struct_malloc[1]:
        State.loc = ""
        if "malloc" not in State.procs:
            assert not State.config.struct_malloc[0],\
                "Malloc procedure not found while struct_malloc is enabled"
            State.config.config["struct_malloc"] = False
        else:
            proc = State.procs["malloc"]
            if proc.in_stack != [Int()]:
                assert not State.config.struct_malloc[0],\
                    "Malloc must take one integer, disable struct_malloc if you don't want the compiler to use malloc"
                State.config.config["struct_malloc"] = False
            if proc.out_stack != [Ptr()]:
                assert not State.config.struct_malloc[0],\
                    "Malloc must return one pointer, disable struct_malloc if you don't want the compiler to use malloc"
                State.config.config["struct_malloc"] = False
        if State.config.struct_malloc[1]:
            State.add_proc_use(proc)

    if is_main and len(State.runtimed_types_list):
        State.loc = ""
        for struct in State.TYPE_STRUCTS:
            assert struct in State.structures,\
                f"If types in runtime are used type.cn must be included from std. Structure {struct} not found."

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

    if is_main:
        ops.extend([Op(OpType.OPERATOR, Operator.DROP) 
            for _ in range(len(stack))])

    return stack


def process_for_in(op: Op, stack: List[Type], iter_stack: list) -> list:
    """
    Type checks and desugars the FOR operation with type of in.
    Returns the result of desugaring as a list of operations.
    """
    type_ = iter_stack[0]
    check_stack(iter_stack, [Ptr(Array())])
    type_ = type_.typ
    State.ops_by_ips[op.operand[0].end].operand = (*op.operand[:2], type_)
    if type_.len == 0:
        return []
    State.route_stack.append(("for", stack.copy(), False))
    State.bind_stack.extend((Int(), type_.typ))
    if State.config.re_IOR:
        State.locs_to_include.append(op.loc)
    op.operand[0].type = BlockType.WHILE
    return [
        Op(OpType.PUSH_INT, 0, loc=op.loc),
        Op(OpType.PUSH_INT, 1, loc=op.loc),
        Op(OpType.WHILE, op.operand[0], loc=op.loc), # TODO:
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
    """
    Type checks and desugars the FOR operation with type of until.
    Returns the result of desugaring as a list of operations.
    """
    check_stack(iter_stack, [Ptr()])
    State.route_stack.append(("for", stack.copy(), False))
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
    """
    Matches type variables with concrete types. Returns a dictionary with one
    pair of id of the VarType object to the actual type if it manages to match,
    if there were no type variable values found returns an empty dict. 
    """
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
    """
    Finds a concrete value for every type variable in `types`.

    Returns a mapping from object ids of VarTypes to concrete types.
    """
    var_types: Dict[int, Type] = {}
    assert len(stack) >= len(types), "Not enough elements on the stack"
    for typ, actual in zip(types, stack):
        var_types = {**match_type_var(typ, actual), **var_types}
    return var_types


def get_concrete_type(typ: Type, var_types: Dict[int, Type]) -> Type:
    """
    Takes a type and a mapping from object ids of VarTypes to their values.

    Returns a concrete type or throws an error if the value of a TypeVar
    couldn't be found in the mapping.
    """
    if isinstance(typ, VarType):
        assert id(typ) in var_types, f'Cannot obtain value for the type variable "{typ.name}"'
        return var_types[id(typ)]
    if isinstance(typ, Ptr):
        return Ptr(get_concrete_type(typ.typ, var_types))
    if isinstance(typ, Array):
        return Array(typ.len, get_concrete_type(typ.typ, var_types))
    return typ


def process_call(op: Op, stack: List[Type]) -> None:
    """
    Type checks an operation with the CALL type.
    """
    in_types: List[object] = []
    out_types: List[object] = []
    var_types = get_var_type_values(
        op.operand.in_stack, stack[-len(op.operand.in_stack):]
    )
    for typ in op.operand.in_stack:
        in_types.append(get_concrete_type(typ, var_types))
    for typ in op.operand.out_stack:
        out_types.append(get_concrete_type(typ, var_types))
    check_stack(stack, in_types)
    stack.extend(out_types)


def type_check_op(op: Op, stack: List[Type]) -> Optional[Union[Op, List[Op]]]:
    """
    Type checks the operation `op` and modifies the stack appropriately.

    Returns either a None, an operation or a list of operations.
    A None means the caller can ignore it. An operation means, that the
    operation provided should be replaced by the returned operation.
    And if a list of operations means the caller must replace the given
    operation with the operations in the list.
    """
    cont_assert(len(OpType) == 40, "Unimplemented type in type_check_op")

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
        assert not must_ptr(State.variables[op.operand]),\
            "variable is automatically a pointer, cannot push a pointer excplicitly"
        stack.append(Ptr(State.variables[op.operand]))
    elif op.type == OpType.PUSH_LOCAL_VAR:
        cont_assert(State.current_proc is not None,
            "Probably bug in parsing with local and global variables")
        if must_ptr(State.current_proc.variables[op.operand]):
            stack.append(Ptr(State.current_proc.variables[op.operand]))
            return Op(OpType.PUSH_LOCAL_VAR_PTR, op.operand, loc=op.loc)
        else:
            stack.append(State.current_proc.variables[op.operand])
    elif op.type == OpType.PUSH_LOCAL_VAR_PTR:
        cont_assert(State.current_proc is not None,
            "Probably bug in parsing with local and global variables")
        assert not must_ptr(State.current_proc.variables[op.operand]),\
            "variable is automatically a pointer, cannot push a pointer excplicitly"

        stack.append(Ptr(State.current_proc.variables[op.operand]))
    elif op.type == OpType.PUSH_STR:
        stack.append(Int())
        stack.append(Ptr())
    elif op.type == OpType.PUSH_NULL_STR:
        stack.append(Ptr())
    elif op.type == OpType.PUSH_PROC:
        stack.append(Addr(op.operand.in_stack, op.operand.out_stack))
    elif op.type == OpType.CAST:
        check_stack(stack, [None])
        stack.append(op.operand)
    elif op.type == OpType.UPCAST:
        assert len(stack) >= 1, "stack is too short"
        struct = stack[-1]
        check_stack(stack, [Ptr()])
        assert isinstance(struct.typ, Struct), "can't upcast non-struct"

        struct = struct.typ
        assert op.operand == struct,\
            f"can't upcast {type_to_str(struct)} to {type_to_str(op.operand)}"

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
        State.route_stack.append(("if-end", stack.copy(), False, []))
    elif op.type == OpType.ELSE:
        original_route = State.route_stack.pop()
        State.route_stack.append(("if-else", stack.copy(), False, [original_route[2]]))
        stack.clear()
        stack.extend(original_route[1])
    elif op.type == OpType.ENDIF:
        route = State.route_stack.pop()
        op.operand.stack_effect = (len(route[1]), len(stack))
        if route[0] == "if-end":
            if route[2]:
                stack.clear()
                stack.extend(route[1])
            else: check_route_stack(stack, route[1])
        else:
            if route[2] and all(route[3]):
                State.route_stack[-1] = (
                    State.route_stack[-1][0], State.route_stack[-1][1],
                    True, State.route_stack[-1][3]
                )
            elif route[2]:
                stack.clear()
                stack.extend(route[1])
            elif not route[3][0]:
                check_route_stack(stack, route[1], "in different routes of if-else")
    elif op.type == OpType.WHILE:
        check_stack(stack, [Int()])
        State.route_stack.append(("while", stack.copy(), False, []))
    elif op.type == OpType.ENDWHILE:
        check_stack(stack, [Int()])
        pre_while_stack = State.route_stack.pop()[1]
        op.operand.stack_effect = (len(pre_while_stack), len(stack))
        check_route_stack(stack, pre_while_stack, "in different routes of while")
    elif op.type == OpType.FOR:
        iter_stack = type_check(op.operand[2])
        assert len(iter_stack) == 1, "iterable expression should return one value"
        if op.operand[1] == "in":
            return process_for_in(op, stack, iter_stack)
        elif op.operand[1] == "until":
            return process_for_until(op, stack, iter_stack)
        else:
            cont_assert(False, "Unimplemented for type in type checking")
    elif op.type == OpType.ENDFOR:
        State.bind_stack.pop()
        State.bind_stack.pop()
        if op.operand[1] == "in":
            if op.operand[2].len == 0:
                return []
            pre_for_stack = State.route_stack.pop()[1]
            check_route_stack(stack, pre_for_stack, "in different routes of for")
            end_while = Op(OpType.ENDWHILE, op.operand[0], loc=op.loc)
            State.ops_by_ips[op.operand[0].end] = end_while
            return [
                Op(OpType.PUSH_BIND_STACK, len(State.bind_stack), loc=op.loc),
                Op(OpType.PUSH_INT, 1, loc=op.loc),
                Op(OpType.OPERATOR, Operator.ADD, loc=op.loc),
                Op(OpType.OPERATOR, Operator.DUP, loc=op.loc),
                Op(OpType.PUSH_INT, op.operand[2].len, loc=op.loc),
                Op(OpType.OPERATOR, Operator.LT, loc=op.loc),
                Op(OpType.UNBIND, (2, True), loc=op.loc),
                end_while,
                Op(OpType.OPERATOR, Operator.DROP, loc=op.loc),
            ]
        elif op.operand[1] == "until":
            pre_for_stack = State.route_stack.pop()[1]
            check_route_stack(stack, pre_for_stack, "in different routes of for")

            if State.config.re_NPD:
                State.locs_to_include.append(op.loc)
            end_while = Op(OpType.ENDWHILE, op.operand[0], loc=op.loc)
            State.ops_by_ips[op.operand[0].end] = end_while
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
                Op(OpType.UNBIND, (2, True), loc=op.loc),
                end_while,
            ]
    elif op.type == OpType.BIND:
        assert len(stack) >= op.operand, "stack is too short for bind"
        State.bind_stack.extend(stack[-op.operand:])
        stack[-op.operand:] = []
    elif op.type == OpType.UNBIND:
        if not op.operand[1]: return
        for _ in range(op.operand[0]):
            State.bind_stack.pop()
    elif op.type == OpType.PUSH_BIND_STACK:
        typ = State.bind_stack[op.operand[0]]
        if op.operand[1] == "base":
            assert typ == Ptr(), "Binded value self must be a pointer to use base"
            assert isinstance(typ.typ, Struct), "Binded value self must be a pointer to a structure to use base"
            assert typ.typ.parent is not None, f'Structure "{typ.typ.name}" does not have a parent'

            stack.append(Ptr(typ.typ.parent))
        else:
            stack.append(State.bind_stack[op.operand[0]])
        return Op(OpType.PUSH_BIND_STACK, op.operand[0], loc=op.loc, loc_id=op.loc_id)
    elif op.type == OpType.DEFPROC:
        State.route_stack.append(("proc", stack.copy(), False, []))
        stack.clear()
        stack.extend(op.operand.in_stack)
        State.current_proc = op.operand
    elif op.type == OpType.PROC_RETURN:
        check_route_stack(
            stack, State.get_proc_by_block(op.operand[0]).out_stack,
            can_collapse_stack=False, error="in procedure definition",
        )
        stack.clear()
        if op.operand[1]:
            stack.extend(State.route_stack.pop()[1])
            State.current_proc = None
        else:
            State.route_stack[-1] = (State.route_stack[-1][0], State.route_stack[-1][1], True, State.route_stack[-1][3])
    elif op.type == OpType.CALL:
        process_call(op, stack)
    elif op.type == OpType.TYPED_LOAD:
        check_stack(stack, [Ptr(op.operand)])
        stack.append(op.operand)
    elif op.type == OpType.PACK:
        struct = State.structures[op.operand[0]]
        if not op.operand[1]:
            cont_assert(stack.pop().typ == struct, "Probably a user now has more control over PACK (_, False)")
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
        assert len(stack) >= 1, "stack is too short"
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        assert isinstance(ptr.typ, Struct),\
            f"can't access field of non-struct : {type_to_str(ptr.typ)}"
        assert op.operand in (*ptr.typ.fields, *ptr.typ.methods),\
            f"field {op.operand} not found on {type_to_str(ptr.typ)}"
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
        assert len(stack) >= 1, "stack is too short"
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        if isinstance(op.operand, int):
            offset = 0
            for typ in ptr.typ.fields_types[:op.operand]:
                offset += sizeof(typ)
            stack.append(Ptr(ptr.typ.fields_types[op.operand]))
            return Op(OpType.PUSH_FIELD_PTR, offset, op.loc)
        assert isinstance(ptr.typ, Struct),\
            f"can't access field of non-struct : {type_to_str(ptr.typ)}"
        assert op.operand in ptr.typ.fields,\
            f"field {op.operand} not found on {type_to_str(ptr.typ)}"
        offset = 0
        for i, j in ptr.typ.fields.items():
            if i == op.operand:
                break
            offset += sizeof(j)
        stack.append(Ptr(ptr.typ.fields[op.operand]))
        return Op(OpType.PUSH_FIELD_PTR, offset, op.loc)
    elif op.type == OpType.CALL_ADDR:
        assert len(stack) >= 1, "The stack is too short"
        predicate = stack.pop()
        assert isinstance(predicate, Addr), f"Predicate must be an addr, but it's {type_to_str(predicate)}"
        check_stack(stack, predicate.in_types.copy())
        stack.extend(predicate.out_types)
        return Op(OpType.CALL_ADDR, predicate)
    elif op.type in (OpType.INDEX, OpType.INDEX_PTR):
        assert len(stack) >= 1, "stack is too short"
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
        assert len(stack) >= 1, "stack is too short"
        _type = stack.pop()
        stack.append(Int())
        for i in range(op.operand):
            assert hasattr(_type, "typ"), f"{type_to_str(_type)} has no type"
            assert _type.typ is not None, f"{type_to_str(_type)} has no type"
            _type = _type.typ

        return Op(OpType.PUSH_INT, sizeof(_type))
    elif op.type == OpType.PUSH_TYPE:
        if isinstance(op.operand, Int):
            stack.append(Ptr(State.structures["Type"]))
        elif isinstance(op.operand, Ptr):
            stack.append(Ptr(State.structures["PtrType"]))
        elif isinstance(op.operand, Addr):
            stack.append(Ptr(State.structures["AddrType"]))
        elif isinstance(op.operand, Array):
            stack.append(Ptr(State.structures["ArrayType"]))
    elif op.type == OpType.SYSCALL:
        check_stack(stack, [None] * (op.operand + 1))
        stack.append(None)
    elif op.type == OpType.OPERATOR:
        return type_check_operator(op, stack)
    elif op.type in (OpType.AUTO_INIT, OpType.ASM):
        pass  # These operations are a generation thing
    else:
        cont_assert(False, f"unknown op type in type_check_op: {op.type.name}")

    return None


def type_check_operator(op: Op, stack: List[Type]) -> Optional[Union[Op, List[Op]]]:
    """
    Type checks the operation of type OPERATOR `op` and modifies the stack appropriately.

    Returns either a None, an operation or a list of operations.
    A None means the caller can ignore it. An operation means, that the
    operation provided should be replaced by the returned operation.
    And if a list of operations means the caller must replace the given
    operation with the operations in the list.
    """

    cont_assert(len(Operator) == 20, "Unimplemented operator in type_check_operator")

    if op.operand in (
        Operator.ADD, Operator.SUB, Operator.MUL, Operator.GT, Operator.LT, 
        Operator.EQ, Operator.LE, Operator.GE, Operator.NE,
    ):
        assert len(stack) >= 2, "stack is too short"
        type2 = stack.pop()
        type1 = stack.pop()
        if type1 == Int() and type2 == Int():
            stack.append(Int())
        elif type1 == Ptr() and type2 == Ptr():
            if isinstance(type1.typ, Struct):
                assert type1.typ is not None and type2.typ is not None,\
                    f"incompatible types for {op.operand.name.lower()}"
                assert type1.typ == type2.typ or type2.typ == type1.typ,\
                    f"can't perform operation on different types: {type_to_str(type1.typ)} and {type_to_str(type2.typ)}"
                assert f"__{op.operand.name.lower()}__" in type1.typ.methods,\
                    f"method __{op.operand.name.lower()}__ not found on {type_to_str(type1.typ)}"
                method = type1.typ.methods[f"__{op.operand.name.lower()}__"]
                stack.extend(method.out_stack)
                State.add_proc_use(method)
                return [
                    Op(OpType.OPERATOR, Operator.SWAP, loc=op.loc),
                    Op(OpType.CALL, method, loc=op.loc),
                ]
            else:
                State.throw_error(f"can't perform an operation on {type_to_str(type1)} and {type_to_str(type2)}")
        else:
            State.throw_error(f"incompatible types for {op.operand.name.lower()}")
    elif op.operand == Operator.DIV:
        assert len(stack) >= 2, "stack is too short"
        type2 = stack.pop()
        type1 = stack.pop()
        if type1 == Int() and type2 == Int():
            stack.extend([Int(), Int()])
        elif type1 == Ptr() and type2 == Ptr():
            if isinstance(type1.typ, Struct):
                assert type1.typ == type2.typ,\
                    f"can't perform operation on different types: {type_to_str(type1.typ)} and {type_to_str(type2.typ)}"
                assert f"__div__" in type1.typ.methods,\
                    f"method __div__ was not found on {type_to_str(type1.typ)}"	
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
        assert len(stack) >= 1, "stack is too short"
        stack.append(stack[-1])
    elif op.operand == Operator.DROP:
        check_stack(stack, [None])
    elif op.operand == Operator.SWAP:
        assert len(stack) >= 2, "stack is too short"
        stack[-2], stack[-1] = stack[-1], stack[-2]
    elif op.operand == Operator.ROT:
        assert len(stack) >= 3, "stack is too short"
        stack[-3], stack[-2], stack[-1] = stack[-1], stack[-2], stack[-3]
    elif op.operand == Operator.OVER:
        assert len(stack) >= 2, "stack is too short"
        stack.append(stack[-2])
    elif op.operand in (Operator.STORE, Operator.STRONG_STORE):
        assert len(stack) >= 1, "stack is too short"
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
        assert len(stack) >= 1, "stack is too short"
        ptr = stack[-1]
        check_stack(stack, [Ptr()])
        State.locs_to_include.append(op.loc)
        op.loc_id = len(State.locs_to_include) - 1
        if ptr.typ is None:
            stack.append(Int())
        elif ptr.typ == Array():
            State.throw_error("can't unpack array to stack")
        elif isinstance(ptr.typ, Struct):
            assert ptr.typ.is_unpackable, f"can't unpack {type_to_str(ptr.typ)}"
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
        cont_assert(False, f"Unimplemented operator in type_check_operator {op.operand.name}")

    return None
