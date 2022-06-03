import os

from compile_eval.compile_eval import evaluate_block
from type_checking.types import parse_type, sizeof

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
    "<" : Operator.LT,
    ">" : Operator.GT,
    "<=" : Operator.LE,
    ">=" : Operator.GE,
    "==" : Operator.EQ,
    "!=" : Operator.NE,
    "!" : Operator.STORE,
    "!8" : Operator.STORE8,
    "@" : Operator.LOAD,
    "@8" : Operator.LOAD8,
    "print" : Operator.PRINT,
}
END_TYPES = {
    BlockType.IF : OpType.ENDIF,
    BlockType.ELSE : OpType.ENDIF,
    BlockType.WHILE : OpType.ENDWHILE,
    BlockType.PROC : OpType.ENDPROC,
    BlockType.BIND : OpType.UNBIND,
}

assert len(Operator) == len(OPERATORS), "Unimplemented operator in parsing.py"
assert len(OpType) == 25, "Unimplemented type in parsing.py"
assert len(BlockType) == len(END_TYPES), "Unimplemented block type in parsing.py"

def lex_string(string: str) -> Op | None:
    start_string = False
    end_string = False

    if string.startswith("\""):
        start_string = True
    if string.endswith("\""):
        end_string = True
    if string.startswith("n\""):
        start_string = True
        State.is_null = True
        string = string[1:]

    if start_string:
        string = string[1:]
        if State.is_string:
            State.throw_error("string litteral was opened without closing previous one")
        State.is_string = True
        State.string_buffer = ""

    if end_string:  
        string = string[:-1]
        if not State.is_string:
            State.throw_error("string litteral was closed without opening")

        res = State.string_buffer + " " + string
        if start_string:
            res = res[1:]
        res = bytes(res, "raw_unicode_escape").decode("unicode_escape")
        State.string_data.append(bytes(res, "utf-8"))
        optype = OpType.PUSH_NULL_STR if State.is_null else OpType.PUSH_STR
        if State.is_null:
            State.string_data[-1] += bytes("\0", "utf-8")

        State.is_string = False
        State.is_null = False
        return Op(optype, len(State.string_data) - 1, State.loc)

    if State.is_string:
        State.string_buffer += " " + string
        if start_string:
            State.string_buffer = State.string_buffer[1:] 

    return None

def lex_token(token: str) -> Op | None | list:
    assert len(OpType) == 25, "Unimplemented type in lex_token"

    if State.is_unpack and token != "struct":
        State.throw_error("unpack must be followed by struct")

    string = lex_string(token)
    if string:
        return string
    if State.is_string:
        return None

    if token in OPERATORS:
        return Op(OpType.OPERATOR, OPERATORS[token])

    elif token.startswith("syscall") and "0" <= token[7] <= "6" and len(token) == 8:
        return Op(OpType.SYSCALL, int(token[7]))

    elif token.isnumeric():
        return Op(OpType.PUSH_INT, int(token) % 2**64)

    elif token == "if":
        block = Block(BlockType.IF, -1)
        State.block_stack.append(block)
        return Op(OpType.IF, block)

    elif token == "end":
        if len(State.block_stack) <= 0:
            State.throw_error("block for end not found")
        block = State.block_stack.pop()
        if block.type == BlockType.BIND:
            unbinded = State.ops_by_ips[block.start].operand
            op = Op(OpType.UNBIND, unbinded)
            State.bind_stack = State.bind_stack[:-unbinded]
        elif block.type == BlockType.PROC:
            State.current_proc = None
            op = Op(OpType.ENDPROC, block)
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
        return op 

    elif token == "memory":
        name = next(State.tokens)
        size = next(State.tokens)
        if not size[0].isnumeric():
            State.loc = size[1]
            State.throw_error("memory size is not a number") 
        State.check_name(name, "memory")
        Memory.new_memory(name[0], int(size[0]))
        return None

    elif token == "var":
        name = next(State.tokens)
        _type = parse_type(next(State.tokens), "variable", False) 
        State.check_name(name, "variable")
        Memory.new_memory(name[0], sizeof(_type))
        if State.current_proc is not None:
            State.current_proc.variables[name[0]] = _type
        else:
            State.variables[name[0]] = _type
        return None

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
        name = next(State.tokens)
        name_value = name[0]
        in_types: list[type] = []
        out_types: list[type] = []

        if State.current_proc is not None:
            sys.stderr.write(f"\033[1;33mWarning {State.loc}\033[0m: nested procedures arent supported, use at your own risk\n")

        has_contaract = ":" not in name[0]
        try:
            parts = name[0].split(":")
            name_value = parts[0]
            queued_token = (parts[1].strip(), name[1])
            if queued_token[0]:
                State.tokens_queue.append(queued_token)
        except IndexError:
            pass

        State.check_name((name_value, name[1]), "procedure")

        proc_token = ("", "")
        types = in_types
        while ":" not in proc_token[0] and has_contaract:
            try:
                proc_token = next(State.tokens)
            except GeneratorExit:
                State.loc = f"{State.filename}:{name[1]}"
                State.throw_error("proc contract was not closed")
            proc_token_value = proc_token[0].split(":")[0].strip()
            if not proc_token_value:
                break
            elif proc_token_value == "->":
                if types is out_types:
                    State.loc = proc_token[1]
                    State.throw_error("few -> separators was found in proc contract")
                types = out_types
            else:
                types.append(parse_type((proc_token_value, proc_token[1]), "procedure contaract"))

        if has_contaract:
            queued_token = (proc_token[0].split(":")[1].strip(), proc_token[1])
            if queued_token[0]:
                State.tokens_queue.append(queued_token)

        op = Op(OpType.DEFPROC, name_value)
        ip = State.get_new_ip(op)

        block = Block(BlockType.PROC, ip)
        State.procs[name_value] = Proc(name_value, ip, in_types, out_types, block)
        State.current_proc = State.procs[name_value]
        State.block_stack.append(block)

        return op

    elif token == "unpack":
        State.is_unpack = True

    elif token == "struct":
        name = next(State.tokens)
        State.check_name(name, "structure")
        
        current_token = ("", "")
        field_type = -1
        fields = {}
        struct_types = []
        while True:
            try:
                current_token = next(State.tokens)
            except:
                State.loc = f"{State.filename}:{name[1]}"
                State.throw_error("structure definition was not closed")
            if current_token[0] == "end":
                break
            if field_type == -1:
                field_type = parse_type(current_token, "structure definition")
            else:
                if current_token[0] in fields:
                    State.loc = current_token[1]
                    State.throw_error(f"field \"{current_token[0]}\" is already defined in structure")
                fields[current_token[0]] = field_type
                struct_types.append(field_type)
                field_type = -1

        if field_type != -1:
            State.loc = current_token[1]
            State.throw_error("field name was not defined")

        State.structures[name[0]] = Struct(name[0], fields, struct_types, State.is_unpack) # type: ignore
        State.is_unpack = False

        return None

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

        orig_file = State.filename
        State.filename = os.path.basename(os.path.splitext(path)[0])

        with open(path, "r") as f:
            ops = parse_to_ops(f.read())
        
        State.filename = orig_file

        return ops

    elif token in State.bind_stack:
        return Op(OpType.PUSH_BIND_STACK, State.bind_stack.index(token))

    elif token in State.variables:
        return Op(OpType.PUSH_VAR, token)

    elif token in State.memories:
        return Op(OpType.PUSH_MEMORY, State.memories[token].offset)

    elif token in State.structures:
        return Op(OpType.PACK, token)

    elif token in State.procs:
        return Op(OpType.CALL, State.procs[token])

    elif token in State.constants:
        return Op(OpType.PUSH_INT, State.constants[token])

    elif token.startswith("(") and token.endswith(")"):
        return Op(OpType.CAST, parse_type((token[1:-1], State.loc), "cast"))

    elif token.startswith("."):
        return Op(OpType.PUSH_FIELD, token[1:])

    elif State.current_proc is not None:
        if token in State.current_proc.variables:
            return Op(OpType.PUSH_LOCAL_VAR, token)
        elif token in State.current_proc.memories:
            return Op(OpType.PUSH_LOCAL_MEM, State.current_proc.memories[token].offset)
        else:
            State.throw_error(f"unknown token: {token}")

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
    for i, line in enumerate(delete_comments(program).split("\n")):
        for j, token in enumerate(line.split()):
            if State.tokens_queue:
                yield State.tokens_queue.pop(0)
            yield (token, f"{i+1}:{j+1}")

def parse_to_ops(program: str) -> list:
    saver = StateSaver()
    State.tokens = tokens(program)
    ops = []

    for token, loc in State.tokens:
        State.loc = loc
        op = lex_token(token)
        if isinstance(op, list):
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