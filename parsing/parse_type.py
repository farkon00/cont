from state import State
from type_checking.types import *

def parse_type(token: tuple[str, str], error):
    name = token[0]
    if name.startswith("*"):
        assert False, "Typed pointer arent implemented yet"
    elif name == "int":
        return Int()
    elif name == "ptr":
        return Ptr()
    else:
        State.loc = f"{State.filename}:{token[1]}"
        State.throw_error(f"unknown type \"{token[0]}\" in {error}")