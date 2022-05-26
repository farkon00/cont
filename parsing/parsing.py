from .op import *

assert len(Operator) == 4, "Unimplemented operator in parsing.py"
assert len(OpType) == 2, "Unimplemented type in parsing.py"
OPERATORS = {
    "+" : Operator.ADD,
    "-" : Operator.SUB,
    "*" : Operator.MUL,
    "print" : Operator.PRINT,
}

def lex_token(token: str) -> auto:
    assert len(OpType) == 2, "Unimplemented type in lex_token"
    if token in OPERATORS:
        return Op(OpType.OPERATOR, OPERATORS[token])
    elif token.isnumeric():
        return Op(OpType.PUSH_INT, int(token))
    else:
        print(f"Unknown token: {token}")
    

def parse_to_ops(program: str) -> list[Op]:
    ops = []
    for token in program.split():
        ops.append(lex_token(token))
    return ops