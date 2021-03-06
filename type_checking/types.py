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

class Array:
    def __init__(self, len=-1, typ=None):
        self.len = len
        self.typ = typ

    def __eq__(self, other) -> bool:
        if isinstance(other, Array):
            return (self.typ == other.typ and (self.len == other.len or -1 in (self.len, other.len)))\
             or other.typ is None or self.typ is None 
        return False
        
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

class Int:
    def __eq__(self, other) -> bool:
        return isinstance(other, Int) or other is None

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

class Addr:
    def __eq__(self, other) -> bool:
        return isinstance(other, Addr) or other is None

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

def type_to_str(_type):
    """
    Converts cont type object to string
    """
    if isinstance(_type, Int):
        return "int"
    elif isinstance(_type, Addr):
        return "addr"
    elif isinstance(_type, Ptr):
        if _type.typ is not None:
            return "*" + type_to_str(_type.typ)
        else:
            return "ptr"
    elif isinstance(_type, Array):
        return type_to_str(_type.typ) + "[" + str(_type.len) + "]" 
    elif isinstance(_type, Struct):
        return _type.name
    elif _type is None:
        return "any"
    else:
        assert False, f"Unimplemented type in type_to_str: {_type}"

def parse_type(token: tuple[str, str], error, auto_ptr: bool = True, allow_unpack: bool = False, 
               end: str | None = None, throw_exc: bool = True):
    State.loc = f"{State.filename}:{token[1]}"
    name = token[0]
    if end is not None:
        if end in name:
            end_index = name.find(end)
            State.tokens_queue.append((name[end_index+len(end):], token[1]))
            name = name[:end_index] 
            if not name.strip():
                return None
    if name.startswith("*"):
        return Ptr(parse_type((token[0][1:], token[1]), error, auto_ptr, allow_unpack))
    elif name == "int":
        return Int()
    elif name == "ptr":
        return Ptr()
    elif name == "addr":
        return Addr()
    elif name in State.structures:
        if auto_ptr:
            return Ptr(State.structures[name])
        else:
            return State.structures[name]
    elif name.startswith("@") and allow_unpack:
        if name[1:] not in State.structures:
            if throw_exc:
                State.throw_error(f"structure \"{name[1:]}\" was not found")
            else:
                return None
        return State.structures[name[1:]].fields_types
    elif name.startswith("[") and name.endswith("]"):
        if name[1:-1] in State.constants:
            length = State.constants[name[1:-1]]
        elif name[1:-1].isnumeric():
            length = int(name[1:-1])
        else:
            if throw_exc:
                State.throw_error(f"constant \"{name[1:-1]}\" was not found")
            else:
                return None
        arr = Array(length, parse_type(next(State.tokens), error, True, False, end))
        if arr is None:
            if throw_exc:
                State.throw_error("array type was not defined")
            else:
                return None
        return Ptr(arr) if auto_ptr else arr
    else:
        if throw_exc:
            State.throw_error(f"unknown type \"{token[0]}\" in {error}")
        else:
            return None

def sizeof(_type) -> int:
    if isinstance(_type, Int) or isinstance(_type, Ptr) or isinstance(_type, Addr):
        return 8
    elif isinstance(_type, Struct):
        return sum([sizeof(field) for field in _type.fields_types])
    elif isinstance(_type, Array):
        return _type.len * sizeof(_type.typ)
    elif _type is None:
        State.throw_error("cant get size of any")
    else:
        assert False, f"Unimplemented type in sizeof: {type_to_str(_type)}"
    
    return 0 # Mypy, shut up!

def check_contravariant(got: Struct, exp: Struct) -> bool:
    """
    Not recomended to use raw, use check_varient instead
    If you only need contravariant check, refactor this function to work in all cases
    Now it only works with structures
    """
    for i in got.children:
        if i is exp:
            return True
        if check_contravariant(i, exp):
            return True

    return False


def check_varient(got: object, exp: object):
    if isinstance(exp, Int) and isinstance(got, Int):
        return True
    if isinstance(exp, Addr) and isinstance(got, Addr):
        return True
    if isinstance(exp, Ptr) and isinstance(got, Ptr):
        return check_varient(got.typ, exp.typ) or exp.typ is None or got.typ is None
    if isinstance(exp, Array) and isinstance(got, Array):
        return check_varient(got.typ, exp.typ) or exp.typ is None or got.typ is None
    if isinstance(exp, Struct) and isinstance(got, Struct):
        # equal is covariant
        return got == exp or check_contravariant(got, exp)

    return False

def down_cast(type1: object, type2: object) -> object:
    """
    Finds object lower in hierarchy and returns it
    BEFORE CALLING ENSURE, THAT TYPES ARE RELATED
    """
    if type1 == type2:
        return type2
    else:
        return type1