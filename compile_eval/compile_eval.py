from state import *
from parsing.op import *


def evaluate_token(token: str, stack: list):
    if token.isnumeric():
        stack.append(int(token))
    elif token.startswith("0x") and State.is_hex(token[2:]):
        stack.append(int(token[2:], 16))
    elif token.startswith("0b") and State.is_bin(token[2:]):
        stack.append(int(token[2:], 2))
    elif token.startswith("0o") and State.is_oct(token[2:]):
        stack.append(int(token[2:], 8))
    elif token == "+":
        stack.append(stack.pop(-2) + stack.pop())
    elif token == "-":
        stack.append(stack.pop(-2) - stack.pop())
    elif token == "*":
        stack.append(stack.pop(-2) * stack.pop())
    elif token == "div":
        stack.append(stack[-2] // stack[-1])
        stack.append(stack.pop(-2) % stack.pop())
    elif token == "%":
        stack.append(stack.pop(-2) % stack.pop())
    elif token == "/":
        stack.append(stack.pop(-2) // stack.pop())
    elif token == "dup":
        stack.append(stack[-1])
    elif token == "drop":
        stack.pop()
    elif token == "swap":
        stack[-2], stack[-1] = stack[-1], stack[-2]
    elif token == "rot":
        stack[-3], stack[-2], stack[-1] = stack[-1], stack[-2], stack[-3]
    elif token == "over":
        stack.append(stack[-2])
    elif token == ">":
        stack.append(int(stack.pop(-2) > stack.pop()))
    elif token == "<":
        stack.append(int(stack.pop(-2) < stack.pop()))
    elif token == ">=":
        stack.append(int(stack.pop(-2) >= stack.pop()))
    elif token == "<=":
        stack.append(int(stack.pop(-2) <= stack.pop()))
    elif token == "==":
        stack.append(int(stack.pop(-2) == stack.pop()))
    elif token == "!=":
        stack.append(int(stack.pop(-2) != stack.pop()))
    elif token == "and":
        a, b = stack.pop(), stack.pop()
        stack.append(int(a and b))
    elif token == "or":
        a, b = stack.pop(), stack.pop()
        stack.append(int(a or b))
    elif token == "not":
        stack.append(int(not stack.pop()))
    elif token in State.constants:
        stack.append(State.constants[token])
    elif token.split(".", 1)[0] in State.enums:
        parts = token.split(".", 1)
        assert parts[1] in State.enums[parts[0]], f'enum value "{parts[1]}" is not defined'
        stack.append(State.enums[parts[0]].index(parts[1]))
    else:
        State.throw_error(
            f"unknown or unavailiable while compile time evaluation token {token}"
        )


def evaluate_block(orig_loc: str, error: str = "memo"):
    stack: List[int] = []
    while True:
        try:
            token = next(State.tokens)
        except StopIteration:
            break
        State.loc = token[1]
        if token[0] in ("end", ";"):
            assert len(stack) == 1, f"{error} block ended with {len(stack)} elements on the stack"
            return stack[0]
        evaluate_token(token[0], stack)

    State.loc = orig_loc
    State.throw_error(f"end of {error} was not found")
