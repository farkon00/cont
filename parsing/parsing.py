from .op import *

OPERATORS = {
    "+" : Operator.ADD,
    "-" : Operator.SUB,
    "print" : Operator.PRINT,
}

def lex_token(token: str) -> auto:
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