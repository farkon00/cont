from .op import *

assert len(Operator) == 5, "Unimplemented operator in parsing.py"
assert len(OpType) == 2, "Unimplemented type in parsing.py"
OPERATORS = {
    "+" : Operator.ADD,
    "-" : Operator.SUB,
    "*" : Operator.MUL,
    "div" : Operator.DIV,
    "print" : Operator.PRINT,
}

def lex_token(token: str) -> Op:
    assert len(OpType) == 2, "Unimplemented type in lex_token"
    if token in OPERATORS:
        return Op(OpType.OPERATOR, OPERATORS[token])
    elif token.isnumeric():
        return Op(OpType.PUSH_INT, int(token))
    else:
        print(f"Unknown token: {token}")
    return Op(OpType.PUSH_INT, 0) # mypy, shut up
    

def parse_to_ops(program: str) -> list:
    ops = []
    for token in program.split():
        ops.append(lex_token(token))
    return ops