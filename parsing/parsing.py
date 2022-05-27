from .op import *
from state import *

assert len(Operator) == 9, "Unimplemented operator in parsing.py"
assert len(OpType) == 5, "Unimplemented type in parsing.py"
assert len(BlockType) == 2, "Unimplemented block type in parsing.py"

OPERATORS = {
    "+" : Operator.ADD,
    "-" : Operator.SUB,
    "*" : Operator.MUL,
    "div" : Operator.DIV,
    "dup" : Operator.DUP,
    "drop" : Operator.DROP,
    "swap" : Operator.SWAP,
    "rot" : Operator.ROT,
    "print" : Operator.PRINT,
}
END_TYPES = {
    BlockType.IF : OpType.ENDIF,
    BlockType.ELSE : OpType.ENDIF,
}

def lex_token(token: str) -> Op:
    assert len(OpType) == 5, "Unimplemented type in lex_token"
    assert len(BlockType) == 2, "Unimplemented block type in parsing.py"

    if token in OPERATORS:
        return Op(OpType.OPERATOR, OPERATORS[token])
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
        return Op(END_TYPES[block.type], block.end)
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
    else:
        print(f"Unknown token: {token}")
    return Op(OpType.PUSH_INT, 0) # mypy, shut up
    

def parse_to_ops(program: str) -> list:
    ops = []
    for token in program.split():
        ops.append(lex_token(token))
    return ops