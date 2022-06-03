from state import State, Struct

class Ptr:
    def __init__(self, typ = None):
        self.typ = typ

    def __eq__(self, other) -> bool:
        if isinstance(other, Ptr):
            return self.typ == other.typ or other.typ is None or self.typ is None 
        return False
        
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

class Int:
    def __eq__(self, other) -> bool:
        return isinstance(other, Int) or other == None

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

def type_to_str(_type):
    """
    Converts cont type object to string
    """
    if isinstance(_type, Int):
        return "int"
    elif isinstance(_type, Ptr):
        if _type.typ is not None:
            return "*" + type_to_str(_type.typ)
        else:
            return "ptr"
    elif isinstance(_type, Struct):
        return _type.name
    elif _type is None:
        return "any"
    else:
        assert False, f"Unimplemented type in type_to_str: {_type}"

def parse_type(token: tuple[str, str], error, auto_ptr: bool = True):
    State.loc = f"{State.filename}:{token[1]}"
    name = token[0]
    if name.startswith("*"):
        return Ptr(parse_type((token[0][1:], token[1]), error))
    elif name == "int":
        return Int()
    elif name == "ptr":
        return Ptr()
    elif name in State.structures:
        if auto_ptr:
            return Ptr(State.structures[name])
        else:
            return State.structures[name]
    else:
        State.throw_error(f"unknown type \"{token[0]}\" in {error}")

def sizeof(_type) -> int:
    if isinstance(_type, Int) or isinstance(_type, Ptr):
        return 8
    elif isinstance(_type, Struct):
        return sum([sizeof(field) for field in _type.fields_types])
    elif _type is None:
        State.throw_error("Cant get size of any")
    else:
        assert False, f"Unimplemented type in sizeof: {_type}"
    
    return 0 # Mypy, shut up!