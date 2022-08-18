import os

from typing import Iterable

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
    BlockType.PROC : OpType.ENDPROC,
    BlockType.BIND : OpType.UNBIND,
}

assert len(Operator) == len(OPERATORS), "Unimplemented operator in parsing.py"
assert len(OpType) == 38, "Unimplemented type in parsing.py"
assert len(BlockType) == len(END_TYPES), "Unimplemented block type in parsing.py"

def next_proc_contract_token(name: tuple[str, str]) -> tuple[tuple[str, str], str]:
    try:
        proc_token = next(State.tokens)
    except StopIteration:
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error("proc contract was not closed")
    proc_token_value = proc_token[0].split(":")[0].strip()
    State.loc = proc_token[1]

    return proc_token, proc_token_value

def parse_proc_head():
    first_token: tuple[str, str] = next(State.tokens)
    in_types: list[object] = []
    out_types: list[object] = []
    names: list[str] = []
    owner: Ptr | None = None if State.owner is None or State.is_static else Ptr(State.owner) 

    if State.current_proc is not None:
        State.throw_error("nested procedures aren't allowed")

    if first_token[0].startswith("[") and first_token[0].endswith("]"):
        if State.owner is not None:
            State.loc = f"{State.filename}:{first_token[1]}"
            State.throw_error("cannot explicitly specify method's structure inside structure")

        name = next(State.tokens)
        if first_token[0][1:-1] not in State.structures:
            State.loc = State.loc = f"{State.filename}:{first_token[1]}"
            State.throw_error(f"structure {first_token[0][1:-1]} is not defined")
        owner = Ptr(State.structures[first_token[0][1:-1]])
    else:
        name = first_token
    
    name_value = name[0]

    has_contaract = ":" not in name[0]
    try:
        parts = name[0].split(":")
        name_value = parts[0]
        queued_token = (parts[1].strip(), name[1])
        if queued_token[0]:
            State.tokens_queue.append(queued_token)
    except IndexError:
        pass

    if owner is None:
        State.check_name((name_value, name[1]), "procedure")

    proc_token = ("", "")
    types = in_types
    while ":" not in proc_token[0] and has_contaract:
        proc_token, proc_token_value = next_proc_contract_token(name)
        if not proc_token_value:
            break
        elif proc_token_value == "->":
            if types is out_types:
                State.throw_error("few -> separators was found in proc contract")
            types = out_types
        else:
            if proc_token_value.startswith("@") and State.is_named and types is in_types:
                if proc_token_value[1:] not in State.structures:
                    State.throw_error(f"structure {proc_token_value[1:]} was not found")
                struct = State.structures[proc_token_value[1:]]
                names.extend(struct.fields.keys())
                types.extend(struct.fields_types)
                continue
                    
            res = parse_type((proc_token_value, proc_token[1]), "procedure contaract", allow_unpack=True, end=":")
            if isinstance(res, Iterable):
                types.extend(res)
            elif res is None: # If ended in array type
                break
            else:
                types.append(res)
                if State.is_named and types is in_types:
                    proc_token, proc_token_value = next_proc_contract_token(name)
                    if not proc_token_value: State.throw_error("name for argument was not specified")
                    names.append(proc_token_value)
                    

    if has_contaract and ":" in proc_token:
        queued_token = (proc_token[0].split(":")[1].strip(), proc_token[1])
        if queued_token[0]:
            State.tokens_queue.append(queued_token)

    if name_value == "__init__" and out_types:
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error("constructor cannot have out types") 

    if name_value in State.DUNDER_METHODS and owner is not None and\
       not (len(in_types) == 1 and len(out_types) == 1):
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error(f"{name_value} method required to have 1 argument and 1 out type")
    if name_value == "__div__" and owner is not None and\
       not (len(in_types) == 1 and len(out_types) == 2):
        State.loc = f"{State.filename}:{name[1]}"
        State.throw_error(f"{name_value} method required to have 1 argument and 2 out types", False)
        sys.stdout.write("\033[1;34mNote\033[0m: __div__ is called on div operator, not when you call /\n")
        exit()
    if (name_value in State.DUNDER_METHODS or name_value == "__div__") and owner is not None:
        if owner.typ is not in_types[0].typ:
            State.loc = f"{State.filename}:{name[1]}"
            State.throw_error(f"{name_value} must have owner structure as argument")
        if len(in_types) > 1:
            if owner.typ is not in_types[1].typ:
                State.loc = f"{State.filename}:{name[1]}"
                State.throw_error(f"{name_value} must have owner structure as argument")

    block = Block(BlockType.PROC, -1)
    proc = Proc(name_value, -1, in_types, out_types, block, State.is_named, owner)
    op = Op(OpType.DEFPROC, proc)
    ip = State.get_new_ip(op)
    block.start = ip
    proc.ip = ip
    if State.is_static:
        State.owner.static_methods[name_value] = proc
    elif owner is None:
        State.procs[name_value] = proc
    if State.is_named and owner is not None:
        names.insert(0, "self")
    State.current_proc = proc
    State.block_stack.append(block)
    if State.is_named:
        State.is_named = False
        State.bind_stack.extend(names)
        return [op, Op(OpType.BIND, len(names))]
    return op

def parse_struct_begining() -> tuple[Optional[Struct], tuple[str, str]]:
    first_token = next(State.tokens)
    parent = None
    if first_token[0].startswith("(") and first_token[0].endswith(")"):
        if first_token[0][1:-1] not in State.structures:
            State.throw_error(f"structure \"{first_token[0][1:-1]}\" is not defined")
        parent = State.structures[first_token[0][1:-1]]
        name = next(State.tokens)
    else:
        name = first_token
    State.check_name(name, "structure")
    if name[0].endswith(":"):
        sys.stderr.write(f"\033[1;33mWarning {State.filename}:{name[1]}\033[0m: structure definition doesnt need :\n")

    return parent, name

def parse_struct_default(field_type: Any, started_proc: bool, static_started: bool, loc: str) -> tuple[str, int]:
    if field_type != -1:
        State.loc = f"{State.filename}:{loc}"
        State.throw_error("field name was not defined")
    if started_proc:
        State.loc = f"{State.filename}:{loc}"
        State.throw_error("field defenition in methods segment")
    if static_started:
        State.loc = f"{State.filename}:{loc}"
        State.throw_error("field defenition in static segment")

    def_name = next(State.tokens)
    def_value = evaluate_block(def_name[1], "default value")
    return def_name[0], def_value

def parse_struct_proc(struct: Struct, static_started: bool, current_token: tuple[str, str]):
    State.tokens_queue.append(current_token)
    State.owner = struct
    State.is_static = static_started
    ops = parse_until_end()
    State.owner = None
    State.is_static = False
    return ops

def register_struct(name: tuple[str, str], fields: dict[str, object], struct_types: list[object],
                    parent: Optional[Struct], defaults: dict[int, int], is_unpack: bool):
    State.is_unpack = is_unpack
    struct = Struct(name[0], fields, struct_types, parent, defaults)
    State.is_unpack = False
    if parent is not None:
        parent.children.append(struct)
    State.structures[name[0]] = struct
    return struct

def parse_struct() -> Op | list[Op] | None:
    is_unpack = State.is_unpack
    State.is_unpack = False

    parent, name = parse_struct_begining()

    current_token = ("", "")
    field_type: Any = -1
    fields = {} if parent is None else parent.fields.copy()
    struct_types = [] if parent is None else parent.fields_types.copy()
    defaults = {} if parent is None else parent.defaults.copy()

    ops: list[Op] = []
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
            def_name, def_value = parse_struct_default(field_type, started_proc, static_started, current_token[1])
            fields[def_name] = Int()
            defaults[len(struct_types)] = def_value
            struct_types.append(fields[def_name])
            continue
        if current_token[0] in ("proc", "nproc"):
            if not started_proc:
                started_proc = True
                if field_type != -1:
                    State.loc = f"{State.filename}:{current_token[1]}"
                    State.throw_error("field name was not defined")
                struct = register_struct(name, fields, struct_types, parent, defaults, is_unpack)

            ops.extend(parse_struct_proc(struct, static_started, current_token))
            continue
        if field_type == -1:
            if started_proc or static_started:
                State.loc = f"{State.filename}:{current_token[1]}"
                State.throw_error("field defenition in non-field segment")
            field_type = parse_type(current_token, "structure definition")
        else:
            if current_token[0] in fields:
                State.loc = f"{State.filename}:{current_token[1]}"
                State.throw_error(f"field \"{current_token[0]}\" is already defined in structure")
            State.check_name(current_token, "field")
            fields[current_token[0]] = field_type
            struct_types.append(field_type)
            field_type = -1

    if field_type != -1:
        State.loc = f"{State.filename}:{current_token[1]}"
        State.throw_error("field name was not defined")

    if not started_proc:
        struct = register_struct(name, fields, struct_types, parent, defaults, is_unpack)

    return ops

def parse_dot(token: str, allow_var: bool = False, auto_ptr: bool = False) -> list[Op]:
    res = []
    parts = token.split(".")
    if allow_var:
        if token in getattr(State.current_proc, "variables", {}):
            assert State.current_proc is not None
            res.append(Op(OpType.PUSH_LOCAL_VAR if must_ptr(State.current_proc.variables[parts[0]]) else OpType.PUSH_LOCAL_VAR_PTR, token))
            parts = parts[1:]
        elif token in getattr(State.current_proc, "memories", {}) and State.current_proc is not None:
            res.append(Op(OpType.PUSH_LOCAL_MEM, State.current_proc.memories[token].offset))
            parts = parts[1:]
        elif parts[0] in State.variables:
            res.append(Op(OpType.PUSH_VAR if must_ptr(State.variables[parts[0]]) else OpType.PUSH_VAR_PTR, parts[0], State.loc))
            parts = parts[1:]
        elif parts[0] in State.bind_stack:
            res.append(Op(OpType.PUSH_BIND_STACK, State.bind_stack.index(parts[0]), State.loc))
            parts = parts[1:]
    for i in parts:
        res.append(Op(OpType.PUSH_FIELD, i, State.loc))
    
    if auto_ptr and res[-1].type == OpType.PUSH_FIELD:
        res[-1] = Op(OpType.PUSH_FIELD_PTR, res[-1].operand, State.loc)
    
    return res

def is_hex(token: str) -> bool:
    return all(i.lower() in "abcdef1234567890" for i in token)

def is_bin(token: str) -> bool:
    return all(i.lower() in "01" for i in token)

def is_oct(token: str) -> bool:
    return all(i.lower() in "01234567" for i in token)

def lex_token(token: str, ops: list[Op]) -> Op | None | list:
    assert len(OpType) == 38, "Unimplemented type in lex_token"

    if State.is_unpack and token != "struct":
        State.throw_error("unpack must be followed by struct")

    if State.is_init and token != "var":
        State.throw_error("init must be followed by var")

    if State.is_named and token != "proc":
        State.throw_error("init must be followed by proc")

    if token in OPERATORS:
        return Op(OpType.OPERATOR, OPERATORS[token])

    elif token.startswith("syscall") and "0" <= token[7] <= "6" and len(token) == 8:
        return Op(OpType.SYSCALL, int(token[7]))

    elif token.isnumeric():
        return Op(OpType.PUSH_INT, int(token) % 2**64)
    
    elif token.startswith("-") and token[1:].isnumeric():
        return Op(OpType.PUSH_INT, 0x10000000000000000-int(token[1:]))

    elif token.startswith("0x") and is_hex(token[2:]):
        return Op(OpType.PUSH_INT, int(token[2:], 16))
    
    elif token.startswith("0b") and is_bin(token[2:]):
        return Op(OpType.PUSH_INT, int(token[2:], 2))
    
    elif token.startswith("0o") and is_oct(token[2:]):
        return Op(OpType.PUSH_INT, int(token[2:], 8))

    elif (token.startswith("\"") or token.startswith("n\"")) and token.endswith("\""):
        string = bytes(token[1 + token.startswith("n\""):-1], "raw_unicode_escape").decode("unicode_escape")
        State.string_data.append(bytes(string, "utf-8"))
        optype = OpType.PUSH_NULL_STR if token.startswith("n\"") else OpType.PUSH_STR
        if token.startswith("n\""):
            State.string_data[-1] += bytes("\0", "utf-8")
        return Op(optype, len(State.string_data)-1)

    elif token == "if":
        op = Op(OpType.IF, -1)
        block = Block(BlockType.IF, State.get_new_ip(op))
        op.operand = block
        State.block_stack.append(block)
        return op

    elif token == "end":
        if len(State.block_stack) <= 0:
            State.throw_error("block for end not found")
        block = State.block_stack.pop()
        if block.type == BlockType.BIND:
            unbinded = State.ops_by_ips[block.start].operand
            op = Op(OpType.UNBIND, unbinded)
            State.bind_stack = State.bind_stack[:-unbinded]
        elif block.type == BlockType.PROC:
            assert State.current_proc is not None
            proc = State.current_proc
            State.current_proc = None
            op = Op(OpType.ENDPROC, block)
            if proc.is_named:
                State.bind_stack = State.bind_stack[:-len(proc.in_stack)]
                block.end = State.get_new_ip(op)
                return [Op(OpType.UNBIND, len(proc.in_stack)), op]
        elif block.type == BlockType.WHILE:
            cond = State.do_stack.pop()
            for i in cond:
                i.loc = State.loc
            op = Op(OpType.ENDWHILE, block, State.loc)
            op.operand.end = State.get_new_ip(op)
            return [*cond, op]
        else:
            op = Op(END_TYPES[block.type], block)

        block.end = State.get_new_ip(op)
        return op

    elif token == "else":
        if len(State.block_stack) <= 0:
            State.throw_error("if for else not found")
        
        block = State.block_stack.pop()
        
        if block.type != BlockType.IF:
            State.throw_error("else without if")

        new_block = Block(BlockType.ELSE, block.end)
        State.block_stack.append(new_block)

        op = Op(OpType.ELSE, new_block)
        block.end = State.get_new_ip(op)
        new_block.start = block.end
        return op

    elif token == "while":
        block = Block(BlockType.WHILE, -1)
        op = Op(OpType.WHILE, block)
        block.start = State.get_new_ip(op)
        State.block_stack.append(block)
        State.do_stack.append([])
        return op

    elif token == "do":
        if len(State.block_stack) <= 0:
            State.throw_error("block for do not found")
        if State.block_stack[-1].type == BlockType.IF:
            if not State.ops_by_ips[State.block_stack[-1].start].compiled:
                State.throw_error("do without if")

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

    elif token == "memory":
        name = next(State.tokens)
        size = next(State.tokens)
        if not size[0].isnumeric() and size[0] not in State.constants:
            State.loc = size[1]
            State.throw_error(f"constant \"{size[0]}\" was not found") 
        State.check_name(name, "memory")
        if size[0].isnumeric():
            Memory.new_memory(name[0], int(size[0]))
        else:
            Memory.new_memory(name[0], State.constants[size[0]])
        return None

    elif token == "var":
        name = next(State.tokens)
        _type = parse_type(next(State.tokens), "variable", False) 
        State.check_name(name, "variable")
        mem = Memory.new_memory(name[0], sizeof(_type))
        if State.is_init and _type != Array(typ=Ptr()):
            State.throw_error(f"cannot auto init variable with type {type_to_str(_type)}")
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
                    Op(OpType.PUSH_VAR_PTR if State.current_proc is None else OpType.PUSH_LOCAL_VAR_PTR, name[0], State.loc),
                    Op(OpType.OPERATOR, Operator.STORE, State.loc)
                ]
            else:
                State.tokens_queue.append(next_token)
        except StopIteration:
            pass

        if is_init:
            if State.current_proc is None:
                Memory.global_offset += sizeof(_type.typ.typ) * _type.len
            else:
                State.current_proc.memory_size += sizeof(_type.typ.typ) * _type.len
            return Op(OpType.AUTO_INIT, (mem, State.get_new_ip(Op(OpType.AUTO_INIT))), loc=State.loc) if _type.len > 0 else None 

    elif token == "memo":
        name = next(State.tokens)
        State.check_name(name, "memory")
        size = evaluate_block(State.loc)
        Memory.new_memory(name[0], size)
        return None

    elif token == "const":
        name = next(State.tokens)
        State.check_name(name)
        State.constants[name[0]] = evaluate_block(State.loc)
        return None

    elif token == "sizeoftype":
        _type = parse_type(next(State.tokens), "size", False)
        return Op(OpType.PUSH_INT, sizeof(_type))
    
    elif token == "bind":
        binded = 0
        name_token = ("", "")
        while ":" not in name_token[0]:
            name_token = next(State.tokens)
            parts = name_token[0].split(":") 
            name = parts[0]
            if len(parts) > 1:
                queued_token = (parts[1].strip(), name_token[1])
                if queued_token[0]:
                    State.tokens_queue.append(queued_token)
            if not name:
                continue
            if name in State.procs or name in State.memories:
                State.loc = name_token[1]
                State.throw_error(f"name for bind \"{name}\" is already taken")
            State.bind_stack.append(name)
            binded += 1
        op = Op(OpType.BIND, binded)
        State.block_stack.append(Block(BlockType.BIND, State.get_new_ip(op)))
        return op
        
    elif token == "proc":
        return parse_proc_head()
    elif token == "nproc":
        State.is_named = True
        return parse_proc_head()

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
        values: list[str] = []
        while True:
            current_token = next(State.tokens)
            if current_token[0] == "end":
                break
            if current_token[0] in values:
                State.loc = f"{State.filename}:{current_token[1]}"
                State.throw_error(f"enum value \"{current_token[0]}\" is already defined")
            values.append(current_token[0])

        State.enums[name[0]] = values
        return None

    elif token == "asm":
        asm = ""
        while True:
            try:
                current_asm_token = next(State.tokens)
            except StopIteration:
                return Op(OpType.ASM, asm)
            if current_asm_token[1].split(":")[-2] == State.loc.split(":")[-2]:
                asm += current_asm_token[0] + " "
            else:
                State.tokens_queue.append(current_asm_token)
                break

        return Op(OpType.ASM, asm)

    elif token == "include":
        name = next(State.tokens)

        path = ""
        std_path = os.path.join(State.dir + "/std/", name[0])

        if os.path.exists(name[0]):
            path = name[0]
        elif os.path.exists(std_path):
            path = std_path
        else:
            State.loc = name[1]
            State.throw_error(f"include file \"{name[0]}\" not found")

        if os.path.abspath(path) in State.included_files:
            return []

        State.included_files.append(os.path.abspath(path))

        orig_file = State.filename
        State.filename = os.path.basename(os.path.splitext(path)[0])

        with open(path, "r") as f:
            ops = parse_to_ops(f.read())
        
        State.filename = orig_file

        return ops

    elif token == "call_like":
        name = next(State.tokens)
        if name[0] not in State.procs:
            State.loc = name[1]
            State.throw_error(f"procedure \"{name[0]}\" is not defined")
        return Op(OpType.CALL_LIKE, State.procs[name[0]])

    elif token == "[]":
        return Op(OpType.INDEX)

    elif token == "*[]":
        return Op(OpType.INDEX_PTR)

    # Checks for token starting with sizeof and ending with any number of @
    elif token.startswith("sizeof") and all([i == "@" for i in token[6:]]):
        return Op(OpType.SIZEOF, len(token) - 6)

    elif token in State.bind_stack:
        return Op(OpType.PUSH_BIND_STACK, State.bind_stack.index(token))

    elif token in getattr(State.current_proc, "variables", {}):
        return Op(OpType.PUSH_LOCAL_VAR, token)

    elif token.startswith("*") and token[1:] in getattr(State.current_proc, "variables", {}):
        return Op(OpType.PUSH_LOCAL_VAR_PTR, token[1:])
    
    elif token in getattr(State.current_proc, "memories", {}) and State.current_proc is not None:
        return Op(OpType.PUSH_LOCAL_MEM, State.current_proc.memories[token].offset)

    elif token in State.variables:
        return Op(OpType.PUSH_VAR, token)

    elif token.startswith("*") and token[1:] in State.variables:
        return Op(OpType.PUSH_VAR_PTR, token[1:])

    elif token in State.memories:
        return Op(OpType.PUSH_MEMORY, State.memories[token].offset)

    elif token in State.structures:
        return Op(OpType.PACK, token)

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
            Op(OpType.OPERATOR, Operator.STORE, State.loc)
        ]

    elif token.startswith("!"):
        _type = parse_type((token[1:], State.loc), "store type", throw_exc=False)
        if _type is not None:
            return Op(OpType.TYPED_STORE, _type)
        else:
            return [
                *parse_dot(token[1:], allow_var=True, auto_ptr=True),
                Op(OpType.OPERATOR, Operator.STORE, State.loc)
            ]

    elif token.startswith("*") and token[1:] in State.procs:
        State.add_proc_use(State.procs[token[1:]].ip)
        return Op(OpType.PUSH_PROC, State.procs[token[1:]].ip)

    elif token.split(".", 1)[0][1:] in State.bind_stack or\
         token.split(".", 1)[0][1:] in State.variables and token.split(".", 1)[0].startswith("*"):
        return parse_dot(token[1:], True, True)

    elif token.split(".", 1)[0] in State.bind_stack or token.split(".", 1)[0] in State.variables:
        return parse_dot(token, True)

    elif token.split(".", 1)[0] in State.enums:
        parts = token.split(".", 1)
        if parts[1] not in State.enums[parts[0]]:
            State.throw_error(f"enum value \"{parts[1]}\" is not defined")
        return Op(OpType.PUSH_INT, State.enums[parts[0]].index(parts[1]))

    elif token.split(".", 1)[0] in State.structures:
        parts = token.split(".", 1)
        if parts[1] not in State.structures[parts[0]].static_methods:
            State.throw_error(f"static method \"{parts[1]}\" was not found")
        State.add_proc_use(State.structures[parts[0]].static_methods[parts[1]])
        return Op(OpType.CALL, State.structures[parts[0]].static_methods[parts[1]])

    else:
        State.throw_error(f"unknown token: {token}")
    return None

def delete_comments(program: str) -> str:
    while True:
        index = program.find("//")
        if index == -1:
            break
        end_comm = program.find("\n", index)
        program = program[:index] + program[end_comm if end_comm != -1 else len(program):]
    return program

def tokens(program: str):
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
            elif char == "\"" and not is_escaped:
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

def parse_until_end() -> list[Op]:
    ops: list[Op] = []
    initial_loc = State.loc
    initial_blocks = len(State.block_stack)
    end = False

    for token, loc in State.tokens:
        if token == "end" and len(State.block_stack) - 1 == initial_blocks:
            end = True
        State.loc = f"{State.filename}:{loc}"
        op = lex_token(token, ops)
        
        if isinstance(op, list):
            ops.extend(op)
        elif op is not None:
            op.loc = f"{State.filename}:{loc}"
            ops.append(op)

        if end:
            break

    State.loc = initial_loc

    return ops

def parse_to_ops(program: str, dump_tokens: bool = False) -> list:
    saver = StateSaver()
    State.tokens = tokens(program)
    ops: list[Op] = []

    if dump_tokens:
        print(" ".join([f"'{i[0]}'" for i in State.tokens]))
        exit()

    for token, loc in State.tokens:
        State.loc = f"{State.filename}:{loc}"
        op = lex_token(token, ops)
        if isinstance(op, list):
            for locating_op in op:
                if locating_op.loc == "":
                    locating_op.loc = f"{State.filename}:{loc}"
            ops.extend(op)
            continue
        if op is not None:
            op.loc = f"{State.filename}:{loc}"
            ops.append(op)

    if State.block_stack:
        if State.block_stack[-1].start != -1:
            State.loc = State.ops_by_ips[State.block_stack[-1].start].loc
        State.throw_error("unclosed block")

    saver.load()

    return ops