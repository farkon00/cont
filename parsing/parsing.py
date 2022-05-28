from .op import *
from state import *

assert len(Operator) == 19, "Unimplemented operator in parsing.py"
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
            print("Error: block for end not found")
            exit(0)
        block = State.block_stack.pop()
        block.end = State.get_new_ip()
        return Op(END_TYPES[block.type], block)
    elif token == "else":
        if len(State.block_stack) <= 0:
            print("Error: if for else not found")
            exit(0)
        
        block = State.block_stack.pop()
        
        if block.type != BlockType.IF:
            print("Error: else without if")
            exit(0)

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
        if not size.isnumeric():
            print("Error: memory size not a number")
            exit(0)
        Memory.new_memory(name, int(size))
        return None
    elif token in State.memories:
        return Op(OpType.PUSH_MEMORY, State.memories[token].offset)
    else:
        print(f"Unknown token: {token}")
        exit(0)
    

def parse_to_ops(program: str) -> list:
    ops = []
    tokens = (i for i in program.split())
    State.tokens = tokens
    for token in tokens:
        op = lex_token(token)
        if op is not None:
            ops.append(op)
    return ops