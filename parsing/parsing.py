from .op import *
from state import *

assert len(Operator) == 21, "Unimplemented operator in parsing.py"
assert len(OpType) == 9, "Unimplemented type in parsing.py"
assert len(BlockType) == 3, "Unimplemented block type in parsing.py"

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
}

def lex_token(token: str) -> Op | None:
    assert len(OpType) == 9, "Unimplemented type in lex_token"
    assert len(BlockType) == 3, "Unimplemented block type in parsing.py"

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
        block.end = State.get_new_ip()
        return Op(END_TYPES[block.type], block)
    elif token == "else":
        if len(State.block_stack) <= 0:
            State.throw_error("if for else not found")
        
        block = State.block_stack.pop()
        
        if block.type != BlockType.IF:
            State.throw_error("else without if")

        block.end = State.get_new_ip()

        new_block = Block(BlockType.ELSE, block.end)
        State.block_stack.append(new_block)
        return Op(OpType.ELSE, new_block)
    elif token == "while":
        block = Block(BlockType.WHILE, State.get_new_ip())
        State.block_stack.append(block)
        return Op(OpType.WHILE, block)
    elif token == "memory":
        name = next(State.tokens)
        size = next(State.tokens)
        if not size[0].isnumeric():
            State.loc = size[1]
            State.throw_error("memory size is not a number")
        if name[0] in State.memories:
            State.loc = name[1]
            State.throw_error(f"memory with name \"\" already exists")
        Memory.new_memory(name[0], int(size[0]))
        return None
    elif token in State.memories:
        return Op(OpType.PUSH_MEMORY, State.memories[token].offset)
    else:
        State.throw_error(f"Unknown token: {token}")
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
            yield (token, f"{i}:{j}")

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