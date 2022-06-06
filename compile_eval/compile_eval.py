from state import *
from parsing.op import *

assert len(OpType) == 31, "Unimplemented type in compile_eval.py"
assert len(Operator) == 19, "Unimplemented operator in compile_eval.py"

def evaluate_token(token: str, stack: list):
    if token.isnumeric(): stack.append(int(token))
    elif token == "+": stack.append(stack.pop(-2) + stack.pop())
    elif token == "-": stack.append(stack.pop(-2) - stack.pop())
    elif token == "*": stack.append(stack.pop(-2) * stack.pop())
    elif token == "div": 
        stack.append(stack[-2] // stack[-1])
        stack.append(stack.pop(-2) % stack.pop())
    elif token == "%": stack.append(stack.pop(-2) % stack.pop())
    elif token == "/": stack.append(stack.pop(-2) // stack.pop())
    elif token == "dup": stack.append(stack[-1])
    elif token == "drop": stack.pop()
    elif token == "swap": stack[-2], stack[-1] = stack[-1], stack[-2]
    elif token == "rot": stack[-3], stack[-2], stack[-1] = stack[-1], stack[-2], stack[-3]
    elif token == ">": stack.append(int(stack.pop(-2) > stack.pop()))
    elif token == "<": stack.append(int(stack.pop(-2) < stack.pop()))
    elif token == ">=": stack.append(int(stack.pop(-2) >= stack.pop()))
    elif token == "<=": stack.append(int(stack.pop(-2) <= stack.pop()))
    elif token == "==": stack.append(int(stack.pop(-2) == stack.pop()))
    elif token == "!=": stack.append(int(stack.pop(-2) != stack.pop()))
    elif token in State.memories: stack.append(State.memories[token])
    elif token in State.constants: stack.append(State.constants[token])
    else:
        State.throw_error(f"unknown or unavailiable while compile time evaluation token {token}")

def evaluate_block(orig_loc: str, error: str = "memo"):
    stack: list = []
    while True:
        try:
            token = next(State.tokens)
        except GeneratorExit:
            break
        State.loc = token[1]
        if token[0] == "end":
            if len(stack) != 1:
                State.throw_error(f"{error} block ended with {len(stack)} elements on the stack")
            return stack[0]
        evaluate_token(token[0], stack)

    State.loc = orig_loc
    State.throw_error(f"end of {error} was not found")