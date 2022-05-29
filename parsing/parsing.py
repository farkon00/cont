from .op import *
from state import *
from type_checking.type_checking import ptr

assert len(Operator) == 21, "Unimplemented operator in parsing.py"
assert len(OpType) == 14, "Unimplemented type in parsing.py"
assert len(BlockType) == 4, "Unimplemented block type in parsing.py"

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
    "*int" : Operator.CAST_INT,
    "*ptr" : Operator.CAST_PTR,
    "print" : Operator.PRINT,
}
END_TYPES = {
    BlockType.IF : OpType.ENDIF,
    BlockType.ELSE : OpType.ENDIF,
    BlockType.WHILE : OpType.ENDWHILE,
    BlockType.PROC : OpType.ENDPROC,
}

def check_str_escape(string: str) -> str:
    res = ""
    escaped = False
    for i in string:
        if escaped:
            if i == "n": char = "\n"
            elif i == "t": char = "\t"
            elif i == "r": char = "\r"
            elif i == "\"": char = "\""
            elif i == "\\": char = "\\"
            elif i == "0": char = "\0"
            else: State.throw_error(f"unknown escape sequence: \\{i}")
            escaped = False
        elif i == "\\":
            escaped = True
            char = ""
        else:
            char = i

        res += char

    return res

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

    if end_string:  
        string = string[:-1]
        if not State.is_string:
            State.throw_error("string litteral was closed without opening")

        State.string_data.append(check_str_escape(State.string_buffer + string))
        optype = OpType.PUSH_NULL_STR if State.is_null else OpType.PUSH_STR
        if State.is_null:
            State.string_data[-1] += "\0"

        State.is_string = False
        State.is_null = False
        return Op(optype, len(State.string_data) - 1, State.loc)

    if start_string:
        string = string[1:]
        if State.is_string:
            State.throw_error("string litteral was opened without closing previous one")
        State.is_string = True
        State.string_buffer = ""

    if State.is_string:
        State.string_buffer += string

    return None

def lex_token(token: str) -> Op | None:
    assert len(OpType) == 14, "Unimplemented type in lex_token"
    assert len(BlockType) == 4, "Unimplemented block type in parsing.py"

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
        if name[0] in State.procs or name[0] in State.memories:
            State.loc = name[1]
            State.throw_error(f"name for memory \"{name[0]}\" is already taken")
        Memory.new_memory(name[0], int(size[0]))
        return None
    elif token == "proc":
        name = next(State.tokens)
        in_types: list[type] = []
        out_types: list[type] = []

        if name[0] in State.procs or name[0] in State.memories:
            State.loc = name[1]
            State.throw_error(f"name for procedure \"{name[0]}\" is already taken")

        proc_token = ("", "")
        types = in_types
        while ":" not in proc_token[0]:
            try:
                proc_token = next(State.tokens)
            except GeneratorExit:
                State.loc = name[1]
                State.throw_error("proc contract was not closed")
            proc_token_value = proc_token[0].split(":")[0].strip()
            if not proc_token_value:
                break
            if proc_token_value == "int":
                types.append(int)
            elif proc_token_value == "ptr":
                types.append(ptr)
            elif proc_token_value == "->":
                if types is out_types:
                    State.loc = proc_token[1]
                    State.throw_error("few -> separators was found in proc contract")
                types = out_types
            else:
                State.loc = proc_token[1]
                State.throw_error(f"unknown type \"{proc_token_value}\" in proc contract")

        queued_token = proc_token[0].split(":")[1].strip()
        if queued_token:
            State.tokens_queue.append((queued_token, proc_token[1]))

        op = Op(OpType.DEFPROC, name[0])
        ip = State.get_new_ip(op)

        block = Block(BlockType.PROC, ip)
        State.procs[name[0]] = Proc(name[0], ip, in_types, out_types, block)
        State.block_stack.append(block)

        return op
    elif token in State.memories:
        return Op(OpType.PUSH_MEMORY, State.memories[token].offset)
    elif token in State.procs:
        return Op(OpType.CALL, State.procs[token])
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
    ops = []
    State.tokens = tokens(program)
    for token, loc in State.tokens:
        State.loc = loc
        op = lex_token(token)
        if op is not None:
            op.loc = loc
            ops.append(op)
    return ops