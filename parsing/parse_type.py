from state import State
from type_checking.type_checking import voidf_ptr

def parse_type(token: tuple[str, str], error):
    name = token[0]
    if name.startswith("*"):
        assert False, "Typed pointer arent implemented yet"
    elif name == "int":
        return int
    elif name == "ptr":
        return voidf_ptr
    else:
        State.loc = f"{State.filename}:{token[1]}"
        State.throw_error(f"unknown type \"{token[0]}\" in {error}")