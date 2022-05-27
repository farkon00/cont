from .op import *

assert len(Operator) == 9, "Unimplemented operator in parsing.py"
assert len(OpType) == 2, "Unimplemented type in parsing.py"
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

def lex_token(token: str) -> Op:
    assert len(OpType) == 2, "Unimplemented type in lex_token"
    if token in OPERATORS:
        return Op(OpType.OPERATOR, OPERATORS[token])
    elif token.isnumeric():
        return Op(OpType.PUSH_INT, int(token) % 2**64)
    else:
        print(f"Unknown token: {token}")
    return Op(OpType.PUSH_INT, 0) # mypy, shut up
    

def parse_to_ops(program: str) -> list:
    ops = []
    for token in program.split():
        ops.append(lex_token(token))
    return ops