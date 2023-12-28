import os

from typing import List, Tuple, Dict, Union, Iterable

from compile_eval.compile_eval import evaluate_block
from type_checking.types import *

from .op import *
from state import *

OPERATORS = {
    "+" : Operator.ADD,
    "-" : Operator.SUB,
    "*" : Operator.MUL,
    "div" : Operator.DIV,
    "dup" : Operator.DUP,
    "drop" : Operator.DROP,
    "swap" : Operator.SWAP,
    "rot" : Operator.ROT,
    "over" : Operator.OVER,
    "<" : Operator.LT,
    ">" : Operator.GT,
    "<=" : Operator.LE,
    ">=" : Operator.GE,
    "==" : Operator.EQ,
    "!=" : Operator.NE,
    "!" : Operator.STORE,
    "!!" : Operator.STRONG_STORE,
    "!8" : Operator.STORE8,
    "@" : Operator.LOAD,
    "@8" : Operator.LOAD8,
}
END_TYPES = {
    BlockType.IF : OpType.ENDIF,
    BlockType.ELSE : OpType.ENDIF,
    BlockType.WHILE : OpType.ENDWHILE,
    BlockType.FOR : OpType.ENDFOR,
    BlockType.PROC : OpType.ENDPROC,
    BlockType.BIND : OpType.UNBIND,
}

assert len(Operator) == len(OPERATORS), "Unimplemented operator in parsing.py"
assert len(OpType) == 40, "Unimplemented type in parsing.py"
assert len(BlockType) == len(END_TYPES), "Unimplemented block type in parsing.py"


def safe_next_token(exception: str = "") -> Tuple[str, str]:
    """
    Gets the next token from the global iterator and
    throws an error if the EOF was reached.

    The error message will be `exception` if it's provided,
    "Unexpected end of file" otherwise.

    Returns the token.
    """
    try:
        token = next(State.tokens)
        State.loc = token[1]
    except StopIteration:
        if exception:
            State.throw_error(exception)
        else:
            State.throw_error("Unexpected end of file")

    return token


def next_proc_contract_token(name: Tuple[str, str]) -> Tuple[Tuple[str, str], str]:
    """
    Gets the next token for the procedure contract and handles the colon.

    Returns the tuple of the original token and the true value of the token.
    The true value is the one is the whole or a part of the token value, that
    was cut down to only include the part, that is inside the contract.
    """
    try:
        proc_token = next(State.tokens)
    except StopIteration:
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error("proc contract was not closed")
    parts = proc_token[0].split(":", 1)
    if len(parts) > 1:
        if  parts[1].strip():
            State.tokens_queue.append((parts[1].strip(), proc_token[1]))
    State.loc = proc_token[1]

    return proc_token, parts[0].strip()

def parse_signature(name: Tuple[str, str], var_types_scope: Dict[str, VarType], 
                    end_char: str) -> Tuple[List[Type], List[Type], List[str]]:
    """
    Parses a procedure signature from the global token iterator.

    `end_char` is the character, that denotes the end of the signature
    e. g. a colon if it's a signature for a regular procedure definition

    Returns a tuple of argument types, output types and
    names for named procedures(if the procedure is not named the list is empty).
    """
    in_types: List[Type] = []
    out_types: List[Type] = []
    names: List[str] = []

    proc_token = ("", "")
    types = in_types
    while end_char not in proc_token[0]:
        proc_token, proc_token_value = next_proc_contract_token(name)
        if not proc_token_value:
            break
        elif proc_token_value == "->":
            assert types is not out_types, "few -> separators was found in proc contract"
            types = out_types
        else:
            if (
                proc_token_value.startswith("@") and\
                State.is_named and types is in_types
            ):
                assert proc_token_value[1:] in State.structures,\
                    f"structure {proc_token_value[1:]} was not found"
                struct = State.structures[proc_token_value[1:]]
                names.extend(struct.fields.keys())
                types.extend(struct.fields_types)
                continue

            is_ended, res = parse_type(
                (proc_token_value, f"{State.filename}:{proc_token[1]}"),
                "procedure contaract",
                allow_unpack=True,
                end=end_char,
                var_type_scope=var_types_scope if types is in_types else None,
            )
            if isinstance(res, Iterable):
                types.extend(res)
            elif res is None:  # If ended in array type
                break
            else:
                types.append(res)
                if State.is_named and types is in_types:
                    assert not is_ended, "name for argument was not specified"
                    proc_token, proc_token_value = next_proc_contract_token(name)
                    assert proc_token_value, "name for argument was not specified"
                    names.append(proc_token_value)
            if is_ended:
                break

    if end_char in proc_token:
        queued_token = (proc_token[0].split(end_char)[1].strip(), proc_token[1])
        if queued_token[0]:
            State.tokens_queue.append(queued_token)

    return in_types, out_types, names

def parse_proc_head(self_named: bool = False) -> str:
    """
    Parses the head of a procedure, defines it and returns the operations for the head.
    Does not consume the first token of the definition e. g. "proc".
    """
    first_token: Tuple[str, str] = next(State.tokens)
    owner: Optional[Ptr] = (
        None if State.owner is None or State.is_static else Ptr(State.owner)
    )
    var_types_scope: Dict[str, VarType] = {}
    State.var_type_scopes.append(var_types_scope)

    assert State.current_proc is None, "nested procedures aren't allowed"

    if first_token[0].startswith("[") and first_token[0].endswith("]"):
        if State.owner is not None:
            State.loc = f"{State.filename}:{first_token[1]}"
            State.throw_error("cannot explicitly specify method's owner inside a structure")

        name = next(State.tokens)
        if first_token[0][1:-1] not in State.structures:
            State.loc = State.loc = f"{State.filename}:{first_token[1]}"
            State.throw_error(f"structure {first_token[0][1:-1]} is not defined")
        owner = Ptr(State.structures[first_token[0][1:-1]])
    else:
        name = first_token

    assert not (not owner and self_named), "Non-method procedure cannot be self-named"

    name_value = name[0]

    has_contaract = ":" not in name[0]
    if not has_contaract:
        parts = name[0].split(":")
        name_value = parts[0]
        queued_token = (parts[1].strip(), name[1])
        if queued_token[0]:
            State.tokens_queue.append(queued_token)

    if owner is None:
        State.check_name((name_value, name[1]), "procedure")

    if has_contaract:
        in_types, out_types, names = parse_signature(name, var_types_scope, ":")
    else:
        in_types, out_types, names = [], [], []

    if name_value == "__init__" and out_types:
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error("constructor cannot have out types")

    # TODO: Fix this hell
    if (
        name_value in [*State.ONE_RETURN_DUNDER_METHODS, *State.NOT_SAME_TYPE_DUNDER_METHODS] and\
        owner is not None and\
        not (len(in_types) == 1 and len(out_types) == 1)
    ):
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error(
            f"{name_value} method is required to have 1 argument and 1 out type"
        )
    if (
        name_value == "__div__" and\
        owner is not None and\
        not (len(in_types) == 1 and len(out_types) == 2)
    ):
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error(
            f"{name_value} method is required to have 1 argument and 2 out types", False
        )
        sys.stdout.write(
            "\033[1;34mNote\033[0m: __div__ is called on div operator, not when you call /\n"
        )
        exit()
    if (
        name_value in State.ONE_RETURN_DUNDER_METHODS or\
        name_value == "__div__" and\
        owner is not None and\
        name_value not in State.NOT_SAME_TYPE_DUNDER_METHODS
    ):
        if owner.typ is not in_types[0].typ:
            State.loc = f"{State.filename}:{name[1]}"
            State.throw_error(f"{name_value} must have owner structure as argument")
        if len(in_types) > 1:
            if owner.typ is not in_types[1].typ:
                State.loc = f"{State.filename}:{name[1]}"
                State.throw_error(f"{name_value} must have owner structure as argument")
    if name_value == "__index_ptr__" and owner is not None and\
            not isinstance(out_types[0], Ptr):
        State.throw_error("Method __index_ptr__ must return a pointer")

    State.var_type_scopes.pop()
    block = Block(BlockType.PROC, -1)
    proc = Proc(name_value, -1, in_types, out_types, block, State.is_named, self_named, owner=owner)
    # TODO: Move generating dunder method into its own function  
    generated_ops = []
    prefix_ops = []
    if (
        name_value in State.DUNDER_NEGATION_MAP or
        (name_value == "__index_ptr__" and not must_ptr(out_types[0].typ)) and
        owner is not None
    ):
        generated_block = Block(BlockType.PROC, -1)
        generated_name = "__index__" if name_value == "__index_ptr__" else State.DUNDER_NEGATION_MAP[name_value] 
        generated_proc = Proc(generated_name, -1, in_types, 
            [out_types[0].typ] if name_value == "__index_ptr__" else out_types,
            generated_block, False, False, owner=owner)
        generated_op = Op(OpType.DEFPROC, generated_proc)
        generated_ip = State.get_new_ip(generated_op)
        generated_block.start = generated_ip
        generated_proc.ip = generated_ip
        generated_op_end = Op(OpType.ENDPROC, generated_block)
        generated_block.end = State.get_new_ip(generated_op_end)
        generated_proc.used_procs.add(proc)
        
        if name_value == "__index_ptr__":
            generated_ops = [
                generated_op,
                Op(OpType.CALL, proc),
                Op(OpType.OPERATOR, Operator.LOAD),
                generated_op_end
            ]
        else:
            if State.config.target == "fasm_x86_64_linux":
                asm = "pop rax\nnot rax\npush rax"            
            elif State.config.target == "wat64":
                asm = "i64.const -1) (i64.xor"
            else:
                cont_assert(False, "Target not found for dunder negation")
            generated_ops = [
                generated_op,
                Op(OpType.CALL, proc),
                Op(OpType.ASM, asm),
                Op(OpType.PUSH_INT, 0xFFFFFFFFFFFFFFFF),
                Op(OpType.OPERATOR, Operator.EQ),
                generated_op_end
            ]
    if name_value == "__init__" and owner is not None:
        assert isinstance(owner.typ, Struct)
        for field_index, value in owner.typ.defaults.items():
            prefix_ops.extend([
                Op(OpType.PUSH_INT, value),
                Op(OpType.OPERATOR, Operator.OVER),
                Op(OpType.PUSH_FIELD_PTR, field_index),
                Op(OpType.OPERATOR, Operator.STORE)
            ])

    op = Op(OpType.DEFPROC, proc)
    ip = State.get_new_ip(op)
    block.start = ip
    proc.ip = ip
    if State.is_static:
        State.owner.static_methods[name_value] = proc
    elif owner is None:
        State.procs[name_value] = proc
    if State.is_named and owner is not None:
        names.append("self")
    State.current_proc = proc
    State.block_stack.append(block)
    if State.is_named:
        State.is_named = False
        State.bind_stack.extend(names)
        prefix_ops.append(Op(OpType.BIND, len(names)))
    if self_named:
        State.bind_stack.append("self")
        prefix_ops.append(Op(OpType.BIND, 1))
    return [*generated_ops, op, *prefix_ops]


def parse_struct_beginning() -> Tuple[Optional[Struct], Tuple[str, str]]:
    """
    Parses the name of the struct and its parent. Doesn't consume the "struct" token.

    Returns the parent struct(None if there isn't one) and
    the token with the name of the struct. 
    """
    first_token = next(State.tokens)
    parent = None
    if first_token[0].startswith("(") and first_token[0].endswith(")"):
        assert first_token[0][1:-1] in State.structures,\
            f'structure "{first_token[0][1:-1]}" was not defined'
        parent = State.structures[first_token[0][1:-1]]
        name = next(State.tokens)
    else:
        name = first_token
    State.check_name(name, "structure")
    if name[0].endswith(":"):
        sys.stderr.write(
            f"\033[1;33mWarning {State.filename}:{name[1]}\033[0m: structure definition doesn't need :\n"
        )

    return parent, name


def parse_struct_default(
    field_type: Any, started_proc: bool, static_started: bool, loc: str
) -> Tuple[str, int]:
    """
    Parses a field of a struct, that has a default value.
    Doesn't consume the "default" token.

    Returns a tuple of the name and the value. 
    """
    prev_loc = State.loc
    State.loc = f"{State.filename}:{loc}"
    assert field_type == -1, "field name was not defined"
    assert not started_proc, "field defenition in the method segment"
    assert not static_started, "field defenition in the static segment"
    State.loc = prev_loc

    def_name = next(State.tokens)
    def_value = evaluate_block(def_name[1], "default value")
    return def_name[0], def_value


def parse_struct_proc(
    struct: Struct, static_started: bool, current_token: Tuple[str, str]
) -> List[Op]:
    """
    Parses a procedure defined inside a struct definition.

    Returns the list of operations for the procedure. 
    """
    State.tokens_queue.append(current_token)
    State.owner = struct
    State.is_static = static_started
    ops = parse_until_end()
    State.owner = None
    State.is_static = False
    return ops


def register_struct(
    name: Tuple[str, str],
    fields: Dict[str, object],
    struct_types: List[object],
    parent: Optional[Struct],
    defaults: Dict[int, int],
):
    """Creates and registers a struct in the state. """
    struct = Struct(name[0], fields, struct_types, parent, defaults, State.is_unpack)
    State.is_unpack = False
    if parent is not None:
        parent.children.append(struct)
    State.structures[name[0]] = struct
    return struct


def parse_struct() -> List[Op]:
    """
    Parses a structure definition, defines the struct and
    returns the operations for the definition. Does not
    consume the "struct" token.
    """
    parent, name = parse_struct_beginning()
    struct = register_struct(name, {}, [], parent, {})

    current_token = ("", "")
    field_type: Any = -1

    ops: List[Op] = []
    started_proc: bool = False
    static_started: bool = False
    while True:
        try:
            current_token = next(State.tokens)
        except StopIteration:
            State.loc = f"{State.filename}:{name[1]}"
            State.throw_error("structure definition was not closed")
        if current_token[0] == "end":
            break
        if current_token[0] == "static":
            static_started = True
            if field_type != -1:
                State.loc = f"{State.filename}:{current_token[1]}"
                State.throw_error("field name was not defined")
            continue
        if current_token[0] == "default":
            def_name, def_value = parse_struct_default(
                field_type, started_proc, static_started, current_token[1]
            )
            struct.fields[def_name] = Int()
            struct.defaults[len(struct.fields_types)] = def_value
            struct.fields_types.append(struct.fields[def_name])
            continue
        if current_token[0] in ("proc", "nproc", "sproc"):
            if not started_proc:
                started_proc = True
                if field_type != -1:
                    State.loc = f"{State.filename}:{current_token[1]}"
                    State.throw_error("field name was not defined")

            ops.extend(parse_struct_proc(struct, static_started, current_token))
            continue
        if field_type == -1:
            if started_proc or static_started:
                State.loc = f"{State.filename}:{current_token[1]}"
                State.throw_error("field defenition in non-field segment")
            field_type = parse_type((current_token[0], f"{State.filename}:{current_token[1]}"), "structure definition")
        else:
            if current_token[0] in struct.fields:
                State.loc = f"{State.filename}:{current_token[1]}"
                State.throw_error(
                    f'field "{current_token[0]}" is already defined in structure'
                )
            State.check_name(current_token, "field")
            struct.fields[current_token[0]] = field_type
            struct.fields_types.append(field_type)
            field_type = -1

    if field_type != -1:
        State.loc = f"{State.filename}:{current_token[1]}"
        State.throw_error("field name was not defined")

    return ops


def parse_dot(token: str, allow_var: bool = False, auto_ptr: bool = False) -> List[Op]:
    """
    Parses one token, which has multiple parts separated by a dot.
    If `allow_var` is True the first part is allowed to be either of
    the following: local or global variable, local or global memory,
    a bound value, "base" if "self" is on the bind stack.
    All other token have to be fields of structs chained.

    If `auto_ptr` is True the last field acess operation
    will be of type PUSH_FIELD_PTR.

    Returns a list of operation for those tokens.
    """
    res = []
    parts = token.split(".")
    if allow_var:
        if parts[0] in getattr(State.current_proc, "variables", {}):
            res.append(
                Op(
                    OpType.PUSH_LOCAL_VAR
                    if must_ptr(State.current_proc.variables[parts[0]])
                    else OpType.PUSH_LOCAL_VAR_PTR,
                    parts[0],
                )
            )
            parts = parts[1:]
        elif parts[0] in getattr(State.current_proc, "memories", {}):
            res.append(
                Op(OpType.PUSH_LOCAL_MEM, State.current_proc.memories[token].offset)
            )
            parts = parts[1:]
        elif parts[0] in State.variables:
            res.append(
                Op(
                    OpType.PUSH_VAR
                    if must_ptr(State.variables[parts[0]])
                    else OpType.PUSH_VAR_PTR,
                    parts[0],
                    State.loc,
                )
            )
            parts = parts[1:]
        elif parts[0] in State.memories:
            res.append(Op(OpType.PUSH_MEMORY, State.memories[parts[0]].offset))
            parts = parts[1:]
        elif parts[0] in State.bind_stack:
            res.append(
                Op(OpType.PUSH_BIND_STACK, (State.bind_stack.index(parts[0]), parts[0]), State.loc)
            )
            parts = parts[1:]
        elif parts[0] == "base":
            assert "self" in State.bind_stack, "You must have a binded value self to use base"
            return Op(OpType.PUSH_BIND_STACK, (State.bind_stack.index("self"), "base")) # TODO: why is this a return?
        else:
            State.throw_error(f'name "{parts[0]}" is not defined')
    for i in parts:
        res.append(Op(OpType.PUSH_FIELD, i, State.loc))

    if auto_ptr and res[-1].type == OpType.PUSH_FIELD:
        res[-1] = Op(OpType.PUSH_FIELD_PTR, res[-1].operand, State.loc)

    return res


def parse_var() -> Union[Op, List[Op]]:
    """
    Parses a variable declaration. Does not consume the "var" token.
    Returns a list of operations or an operation for the declaration.
    """
    # TODO: this function is too long
    name = safe_next_token("Expected variable name")
    type_tok = safe_next_token("Expected variable type")
    _type = parse_type((type_tok[0], f"{State.filename}:{type_tok[1]}"), "variable", False)
    State.check_name(name, "variable")
    mem = Memory.new_memory(name[0], sizeof(_type))
    assert not State.is_init or _type == Array(typ=Ptr()) or isinstance(_type, Struct),\
        f"cannot auto init variable with type {type_to_str(_type)}"
    if State.current_proc is not None:
        State.current_proc.variables[name[0]] = _type
    else:
        State.variables[name[0]] = _type
    is_init = State.is_init
    State.is_init = False
    try:
        next_token = next(State.tokens)
        if next_token[0] == "=":
            if _type != Int():
                State.loc = next_token[1]
                State.throw_error("variable can't be initialized with non-int value")
            value = evaluate_block(name[1], "variable value")
            return [
                Op(OpType.PUSH_INT, value, State.loc),
                Op(
                    OpType.PUSH_VAR_PTR
                    if State.current_proc is None
                    else OpType.PUSH_LOCAL_VAR_PTR,
                    name[0], State.loc
                ),
                Op(OpType.OPERATOR, Operator.STORE, State.loc),
            ]
        else:
            State.tokens_queue.append(next_token)
    except StopIteration:
        pass

    if is_init:
        if isinstance(_type, Struct):
            if "__init__" in _type.methods:
                State.add_proc_use(_type.methods["__init__"])
            return [
                Op(
                    OpType.PUSH_VAR
                    if State.current_proc is None
                    else OpType.PUSH_LOCAL_VAR,
                    name[0],
                    loc=State.loc
                ),
                Op(OpType.PACK, (_type.name, False), loc=State.loc),
                Op(OpType.OPERATOR, Operator.DROP, loc=State.loc)
            ]

        # if the type is an array
        if State.current_proc is None:
            Memory.global_offset += sizeof(_type.typ.typ) * _type.len
        else:
            State.current_proc.memory_size += sizeof(_type.typ.typ) * _type.len
        return (
            Op(
                OpType.AUTO_INIT,
                (mem, State.get_new_ip(Op(OpType.AUTO_INIT))),
                loc=State.loc,
            )
            if _type.len > 0
            else None
        )

    return []


def parse_end() -> Union[List[Op], Op]:
    """
    Parses an "end" token. Modifies all the state required
    to close a block. Does not consume the "end" token itself.

    Returns a list of operations or an operation to end the block.
    """
    assert len(State.block_stack) > 0, "block for end not found"
    block = State.block_stack.pop()
    if block.binded != 0:
        State.bind_stack = State.bind_stack[:-block.binded]
    if block.type == BlockType.BIND:
        unbinded = State.ops_by_ips[block.start].operand
        op = Op(OpType.UNBIND, unbinded)
        State.bind_stack = State.bind_stack[:-unbinded]
    elif block.type == BlockType.PROC:
        proc = State.current_proc
        State.current_proc = None
        op = Op(OpType.ENDPROC, block)
        if proc.is_named:
            State.bind_stack = State.bind_stack[:-len(proc.in_stack)]
            block.end = State.get_new_ip(op)
            return [Op(OpType.UNBIND, len(proc.in_stack) + block.binded), op]
        if proc.is_self_named:
            State.bind_stack = State.bind_stack[:-1]
            block.end = State.get_new_ip(op)
            return [Op(OpType.UNBIND, 1 + block.binded), op]
    elif block.type == BlockType.WHILE:
        cond = State.do_stack.pop()[::-1]
        for i in cond:
            i.loc = State.loc
        op = Op(OpType.ENDWHILE, block, State.loc)
        op.operand.end = State.get_new_ip(op)
        if block.binded != 0:
            return [Op(OpType.UNBIND, block.binded), *cond, op]
        return [*cond, op]
    elif block.type == BlockType.FOR:
        State.bind_stack.pop()
        State.bind_stack.pop()
        op = Op(OpType.ENDFOR, State.ops_by_ips[block.start].operand, State.loc)
        ip = State.get_new_ip(op)
        block.end = ip
    else:
        op = Op(END_TYPES[block.type], block)

    block.end = State.get_new_ip(op)
    if block.binded != 0:
        return [Op(OpType.UNBIND, block.binded), op]
    
    return op


def parse_for() -> Op:
    """
    Parses a head of a for loop. Does not consume the "for" token itself.

    Returns a FOR operation.
    """
    bind         = safe_next_token("bind name for for loop was not found")[0]
    type_        = safe_next_token("separator for for loop was not found")[0]
    itr, itr_loc = safe_next_token("iterator for for loop was not found")

    assert type_ in ("in", "until"),\
        f'unexpected token: expected "in" or "until", got "{type_}"'

    itr_ops = parse_dot(itr, allow_var=True)
    for itr_op in itr_ops:
        itr_op.loc = f"{State.filename}:{itr_loc}"
    block = Block(BlockType.FOR, -1)
    op = Op(OpType.FOR, (block, type_, itr_ops))
    block.start = State.get_new_ip(op)
    State.block_stack.append(block)
    State.bind_stack.extend(("*" + bind, bind))
    return op


def parse_bind(end_char: str = ":", unbind_on_block: bool = False) -> Op:
    """
    Parses a head of a bind block or a let binding.
    Does not consume "bind" or "let" tokens.

    * `end_char` is the character, which is going to end the list of bind names
    * `unbind_on_block` indicates whether the bind will have its own block
    or is going to use the current inner block for unbinding(True indicates the latter)

    Returns a BIND operation.
    """
    binded = 0
    name_token = ("", "")
    while end_char not in name_token[0]:
        name_token = next(State.tokens)
        parts = name_token[0].split(end_char)
        name = parts[0]
        if len(parts) > 1:
            queued_token = (parts[1].strip(), name_token[1])
            if queued_token[0]:
                State.tokens_queue.append(queued_token)
        if not name:
            continue
        State.check_name(name_token, "bind")
        State.bind_stack.append(name)
        binded += 1
    op = Op(OpType.BIND, binded)
    if unbind_on_block:
        if State.block_stack:
            State.block_stack[-1].binded += binded
        else:
            State.global_binded += binded
    else:
        State.block_stack.append(Block(BlockType.BIND, State.get_new_ip(op)))
    return op


def parse_do(ops: List[Op]) -> Op:
    """
    Parses a "do" token, but does not consume it. Does
    the required changes to the operation list `op` for
    the do token.

    Returns an operation for the "do" token.
    """
    assert len(State.block_stack) > 0, "block for do not found"
    if State.block_stack[-1].type == BlockType.IF:
        assert State.ops_by_ips[State.block_stack[-1].start].compiled,\
            "do without if"

        State.ops_by_ips[State.block_stack[-1].start].compiled = False
        return Op(OpType.IF, State.block_stack[-1])
    elif State.block_stack[-1].type == BlockType.WHILE:
        orig_while = State.ops_by_ips[State.block_stack[-1].start]
        orig_while.compiled = False
        for i in reversed(ops):
            if i is orig_while:
                break
            State.do_stack[-1].append(i.copy())
        op = Op(OpType.WHILE, orig_while.operand)
        State.ops_by_ips[State.block_stack[-1].start] = op
        return op
    else:
        State.throw_error("do without if or while")


def include_file() -> List[Op]:
    """
    Includes a cont file using the path in the token
    next in the global iterator. If the file has already
    been included before returns an empty list and does nothing.

    Returns a list of operations for the file.
    """
    name = next(State.tokens)

    path = ""
    std_path = os.path.join(State.dir + "/std/", name[0])

    if os.path.exists(name[0]):
        path = name[0]
    elif os.path.exists(std_path):
        path = std_path
    else:
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error(f'include file "{name[0]}" not found')

    abs_path = os.path.abspath(path)
    if abs_path in State.included_files:
        return []

    State.included_files.append(abs_path)

    orig_file, orig_abs = State.filename, State.abs_path
    State.filename, State.abs_path = os.path.basename(os.path.splitext(path)[0]), abs_path 

    with open(path, "r") as f:
        ops = parse_to_ops(f.read())

    State.filename, State.abs_path = orig_file, orig_abs

    return ops


def parse_token(token: str, ops: List[Op]) -> Union[Op, List[Op]]:
    """
    Parses a token and returns either a list of operation or an operation
    for the token. Might modify the list of operation for the file `ops`.
    """
    cont_assert(len(OpType) == 40, "Unimplemented type in parse_token")

    assert not State.is_unpack or token == "struct", "unpack must be followed by struct"
    assert not State.is_init or token == "var", "init must be followed by var"
    assert not State.is_named or token == "proc", "named must be followed by proc"

    if token in OPERATORS:
        return Op(OpType.OPERATOR, OPERATORS[token])

    elif token.startswith("syscall") and "0" <= token[7] <= "6" and len(token) == 8:
        return Op(OpType.SYSCALL, int(token[7]))

    elif token.isnumeric():
        return Op(OpType.PUSH_INT, int(token) % 2**64)

    elif token.startswith("-") and token[1:].isnumeric():
        return Op(OpType.PUSH_INT, 0x10000000000000000 - int(token[1:]))

    elif token.startswith("0x") and State.is_hex(token[2:]):
        return Op(OpType.PUSH_INT, int(token[2:], 16))

    elif token.startswith("0b") and State.is_bin(token[2:]):
        return Op(OpType.PUSH_INT, int(token[2:], 2))

    elif token.startswith("0o") and State.is_oct(token[2:]):
        return Op(OpType.PUSH_INT, int(token[2:], 8))

    elif (token.startswith('"') or token.startswith('n"')) and token.endswith('"'):
        string = bytes(
            token[1 + token.startswith('n"'):-1], "raw_unicode_escape"
        ).decode("unicode_escape")
        State.string_data.append(bytes(string, "utf-8"))
        optype = OpType.PUSH_NULL_STR if token.startswith('n"') else OpType.PUSH_STR
        if token.startswith('n"'):
            State.string_data[-1] += bytes("\0", "utf-8")
        return Op(optype, len(State.string_data) - 1)

    elif token.startswith("'") and token.endswith("'") and len(token) == 3:
        return Op(OpType.PUSH_INT, ord(token[1]))

    elif token == "if":
        op = Op(OpType.IF, -1)
        block = Block(BlockType.IF, State.get_new_ip(op))
        op.operand = block
        State.block_stack.append(block)
        return op

    elif token == "end":
        return parse_end()

    elif token == "else":
        assert len(State.block_stack) > 0, "if for else not found"

        block = State.block_stack.pop()

        assert block.type == BlockType.IF, "else without if"

        new_block = Block(BlockType.ELSE, block.end)
        State.block_stack.append(new_block)

        op = Op(OpType.ELSE, new_block)
        block.end = State.get_new_ip(op)
        new_block.start = block.end
        if block.binded != 0:
            State.bind_stack = State.bind_stack[:-block.binded]
            return [Op(OpType.UNBIND, block.binded), op]
        else:
            return op

    elif token == "#if":
        cond = evaluate_block(State.loc, "#if condition")
        State.compile_ifs_opened += 1
        State.false_compile_ifs += bool(State.false_compile_ifs) or not cond

    elif token == "#else":
        assert State.compile_ifs_opened, "#else without #if"
        if State.false_compile_ifs < 2:
            State.false_compile_ifs = int(not State.false_compile_ifs)

    elif token == "#endif":
        assert State.compile_ifs_opened != 0, "#endif without #if"
        State.compile_ifs_opened -= 1
        State.false_compile_ifs -= bool(State.false_compile_ifs)

    elif token == "while":
        block = Block(BlockType.WHILE, -1)
        op = Op(OpType.WHILE, block)
        block.start = State.get_new_ip(op)
        State.block_stack.append(block)
        State.do_stack.append([])
        return op

    elif token == "for":
        return parse_for()

    elif token == "do":
        return parse_do(ops)

    elif token == "memory":
        name = next(State.tokens)
        size = next(State.tokens)
        if not size[0].isnumeric() and size[0] not in State.constants:
            State.loc = size[1]
            State.throw_error(f'constant "{size[0]}" was not found')
        State.check_name(name, "memory")
        if size[0].isnumeric():
            Memory.new_memory(name[0], int(size[0]))
        else:
            Memory.new_memory(name[0], State.constants[size[0]])

    elif token == "var":
        return parse_var()

    elif token == "memo":
        name = next(State.tokens)
        State.check_name(name, "memory")
        size = evaluate_block(State.loc, "memo")
        Memory.new_memory(name[0], size)

    elif token == "const":
        name = next(State.tokens)
        State.check_name(name, "constant")
        State.constants[name[0]] = evaluate_block(State.loc, "const")

    elif token == "sizeoftype":
        type_tok = safe_next_token("Expected type to get a size of")
        _type = parse_type((type_tok[0], f"{State.filename}:{type_tok[1]}"), "size", False)
        return Op(OpType.PUSH_INT, sizeof(_type))

    elif token == "bind":
        return parse_bind()
    elif token == "let":
        return parse_bind(end_char=";", unbind_on_block=True)
    elif token == "proc":
        return parse_proc_head()
    elif token == "nproc":
        State.is_named = True
        return parse_proc_head()
    elif token == "sproc":
        assert not State.is_named, "Procedure cannot be named and self-named at the same time"
        return parse_proc_head(self_named=True)

    # prefix tokens
    elif token == "unpack":
        State.is_unpack = True
    elif token == "init":
        State.is_init = True
    elif token == "named":
        State.is_named = True

    elif token == "struct":
        return parse_struct()

    elif token == "enum":
        name = next(State.tokens)
        State.check_name(name, "enum")
        values: List[str] = []
        while True:
            current_token = next(State.tokens)
            if current_token[0] == "end":
                break
            if current_token[0] in values:
                State.loc = f"{State.filename}:{current_token[1]}"
                State.throw_error(f'enum value "{current_token[0]}" is already defined')
            values.append(current_token[0])

        State.enums[name[0]] = values
        if name[0] == "Platform":
            assert "platform" not in State.constants, "Defined enum Platform and constant platform is already defined"
            assert State.config.target in values, "Enum Platform does not have a current platform defined"
            State.constants["platform"] = values.index(State.config.target)

    elif token == "asm":
        asm = safe_next_token()[0]
        assert asm.startswith('"') and asm.endswith('"'), "asm must be followed by a string"

        return Op(OpType.ASM, asm[1:-1])

    elif token == "type":
        type_tok = safe_next_token("Expected a type")
        typ = parse_type((type_tok[0], f"{State.filename}:{type_tok[1]}"), "type")
        if typ not in State.runtimed_types_set:
            State.runtimed_types_set.add(typ)
            State.runtimed_types_list.append(typ)
        return Op(OpType.PUSH_TYPE, typ, token[1])

    elif token == "include":
        return include_file()

    elif token == "call":
        return Op(OpType.CALL_ADDR, None)

    elif token == "#import":
        assert State.config.target == "wat64", "Current target does not support imports"
        
        name, name_loc = safe_next_token("Expected a function name")
        path, _ = safe_next_token("Expected a path")
        State.check_name((name, name_loc))
        if ";" not in name:
            in_types, out_types, _ = parse_signature((name, name_loc), {}, ";")
        else:
            in_types, out_types = [], []

            parts = name.split(";")
            name = parts[0]
            queued_token = (parts[1].strip(), name_loc)
            if queued_token[0]:
                State.tokens_queue.append(queued_token)
        proc = Proc.create_imported(name, in_types, out_types)
        State.procs[name] = proc
        State.imported_procs.append((name, path))

    elif token == "#export":
        assert State.config.target == "wat64", "Current target does not support exports"
        name = safe_next_token("Expected a procedure name")[0]
        assert name in State.procs, f'Procedure "{name}" not found'
        State.used_procs.add(State.procs[name])
        State.procs[name].is_exported = True

    elif token == "[]":
        return Op(OpType.INDEX)

    elif token == "*[]":
        return Op(OpType.INDEX_PTR)

    # Checks for token starting with sizeof and ending with any number of @
    elif token.startswith("sizeof") and all([i == "@" for i in token[6:]]):
        return Op(OpType.SIZEOF, len(token) - 6)

    elif token in State.bind_stack:
        index = len(State.bind_stack) - State.bind_stack[::-1].index(token) - 1 # Search from the right
        return Op(OpType.PUSH_BIND_STACK, (index, token))

    elif token == "base":
        assert "self" in State.bind_stack, "You must have a binded value self to use base"
        return Op(OpType.PUSH_BIND_STACK, (State.bind_stack.index("self"), "base"))

    elif token in getattr(State.current_proc, "variables", {}):
        return Op(OpType.PUSH_LOCAL_VAR, token)

    elif token.startswith("*") and token[1:] in getattr(
        State.current_proc, "variables", {}
    ):
        return Op(OpType.PUSH_LOCAL_VAR_PTR, token[1:])

    elif (
        token in getattr(State.current_proc, "memories", {}) and\
        State.current_proc is not None
    ):
        return Op(OpType.PUSH_LOCAL_MEM, State.current_proc.memories[token].offset)

    elif token in State.variables:
        return Op(OpType.PUSH_VAR, token)

    elif token.startswith("*") and token[1:] in State.variables:
        return Op(OpType.PUSH_VAR_PTR, token[1:])

    elif token in State.memories:
        return Op(OpType.PUSH_MEMORY, State.memories[token].offset)

    elif token in State.structures:
        return Op(OpType.PACK, (token, True))

    elif token in State.procs:
        State.add_proc_use(State.procs[token])
        return Op(OpType.CALL, State.procs[token])

    elif token in State.constants:
        return Op(OpType.PUSH_INT, State.constants[token])

    elif token.startswith("(") and token.endswith(")"):
        return Op(OpType.CAST, parse_type((token[1:-1], State.loc), "cast"))

    elif token.startswith("upcast(") and token.endswith(")"):
        return Op(OpType.UPCAST, parse_type((token[7:-1], State.loc), "upcast", False))

    elif token.startswith(".*"):
        return parse_dot(token[2:], auto_ptr=True)

    elif token.startswith("."):
        return parse_dot(token[1:])

    elif token.startswith("@"):
        _type = parse_type((token[1:], State.loc), "load type")
        return Op(OpType.TYPED_LOAD, _type)

    elif token.startswith("!."):
        return [
            *parse_dot(token[2:], auto_ptr=True),
            Op(OpType.OPERATOR, Operator.STORE, State.loc),
        ]

    elif token.startswith("!"):
        return [
            *parse_dot(token[1:], allow_var=True, auto_ptr=True),
            Op(OpType.OPERATOR, Operator.STORE, State.loc),
        ]

    elif token.startswith("*") and token[1:] in State.procs:
        proc = State.procs[token[1:]]
        State.add_proc_use(proc)
        State.referenced_procs.add(proc)
        return Op(OpType.PUSH_PROC, proc)

    elif (
        token.split(".", 1)[0][1:] in State.bind_stack or\
        token.split(".", 1)[0][1:] in State.variables or\
        token.split(".", 1)[0][1:] in getattr(State.current_proc, "variables", {}) and\
        token.split(".", 1)[0].startswith("*")
    ):
        return parse_dot(token[1:], True, True)

    elif (
        token.split(".", 1)[0] == "base" or\
        token.split(".", 1)[0] in State.bind_stack or\
        token.split(".", 1)[0] in State.variables or\
        token.split(".", 1)[0] in getattr(State.current_proc, "variables", {})
    ):
        return parse_dot(token, True)

    elif token.split(".", 1)[0] in State.enums:
        parts = token.split(".", 1)
        assert parts[1] in State.enums[parts[0]], f'enum value "{parts[1]}" is not defined'
        return Op(OpType.PUSH_INT, State.enums[parts[0]].index(parts[1]))

    elif token.split(".", 1)[0] in State.structures:
        parts = token.split(".", 1)
        assert parts[1] in State.structures[parts[0]].static_methods,\
            f'static method "{parts[1]}" was not found'
        State.add_proc_use(State.structures[parts[0]].static_methods[parts[1]])
        return Op(OpType.CALL, State.structures[parts[0]].static_methods[parts[1]])
    else:
        State.throw_error(f"unknown token: {token}")
    return []


def delete_comments(program: str) -> str:
    """
    Takes a program as a source code string and returns
    the same program without all the comments. 
    """
    while True:
        index = program.find("//")
        if index == -1:
            break
        end_comm = program.find("\n", index)
        program = (
            program[:index] + program[end_comm if end_comm != -1 else len(program):]
        )
    return program


def tokens(program: str) -> Generator[Tuple[str, str], None, None]:
    """
    An iterator, that yields tokens of the program as a
    tuple of the token value and their location in the format of
    "{row}:{column}".
    """
    token = ""
    is_string = False
    is_escaped = False
    for i, line in enumerate(delete_comments(program).split("\n")):
        for j, char in enumerate(line):
            if State.tokens_queue:
                yield State.tokens_queue.pop(0)
            if (char.isspace()) and not is_string:
                if token != "":
                    yield (token, f"{i+1}:{j+1}")
                    token = ""
            elif char == '"' and not is_escaped:
                is_string = not is_string
                token += char
                if not is_string:
                    yield (token, f"{i+1}:{j+1}")
                    token = ""
            elif char == "\\" and is_string and not is_escaped:
                is_escaped = True
                token += char
            elif is_string:
                is_escaped = False
                token += char
            else:
                token += char
        if token != "":
            yield (token, f"{i+1}:{j+1}")
            token = ""


def parse_until_end() -> List[Op]:
    """
    Parses tokens from the global token iterator and returns
    the list of operation for them. Stops parsing, when it meets
    an "end" token, that doesn't match any block inside.
    """
    ops: List[Op] = []
    initial_loc = State.loc
    initial_blocks = len(State.block_stack)
    end = False

    for token, loc in State.tokens:
        if State.false_compile_ifs and token not in ("#if", "#else", "#endif"):
            continue
        if token == "end" and len(State.block_stack) - 1 == initial_blocks:
            end = True
        State.loc = f"{State.filename}:{loc}"
        op = parse_token(token, ops)

        if isinstance(op, list):
            for oper in op:
                if oper.loc == "":
                    oper.loc = f"{State.filename}:{loc}" 
            ops.extend(op)
        elif op is not None:
            op.loc = f"{State.filename}:{loc}"
            ops.append(op)

        if end:
            break

    State.loc = initial_loc

    return ops


def parse_to_ops(program: str, dump_tokens: bool = False, is_main: int = False) -> List[Op]:
    """
    Parses a program from a raw source code string into a
    list of operations. The function should be called exactly one
    time with `is_main` set to True for each compilation.
    
    If `dump_tokens` is set the function will print all the tokens
    to the stdout and exit.

    Returns a list of operations for the program.
    """
    saver = StateSaver()
    State.tokens = tokens(program)
    ops: List[Op] = []

    if dump_tokens:
        print(" ".join([f"'{i[0]}'" for i in State.tokens]))
        exit()

    for token, loc in State.tokens:
        if State.false_compile_ifs and token not in ("#if", "#else", "#endif"):
            continue
        State.loc = f"{State.filename}:{loc}"
        op = parse_token(token, ops)
        if isinstance(op, list):
            for locating_op in op:
                if locating_op.loc == "":
                    locating_op.loc = f"{State.filename}:{loc}"
            ops.extend(op)
            continue
        op.loc = f"{State.filename}:{loc}"
        ops.append(op)

    if State.block_stack:
        if State.block_stack[-1].start != -1:
            State.loc = State.ops_by_ips[State.block_stack[-1].start].loc
        State.throw_error("unclosed block")

    saver.load()

    if is_main and State.global_binded:
        State.bind_stack = []
        ops.append(Op(OpType.UNBIND, State.global_binded))
    return ops
