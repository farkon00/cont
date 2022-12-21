from typing import Optional

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

    def text_repr(self) -> str:
        return f"ptr{'_' + self.typ.text_repr() if self.typ is not None else ''}"

    def __hash__(self) -> int:
        return hash(self.text_repr())

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

    def text_repr(self) -> str:
        assert self.typ is not None
        return f"arr_{self.typ.text_repr()}_{self.len}"

    def __hash__(self) -> int:
        return hash(self.text_repr())

class Int:
    def __eq__(self, other) -> bool:
        return isinstance(other, Int) or other is None

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def text_repr(self) -> str:
        return f"int"

    def __hash__(self) -> int:
        return hash(self.text_repr())

class Addr:
    def __eq__(self, other) -> bool:
        return isinstance(other, Addr) or other is None

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def text_repr(self) -> str:
        return f"addr"

    def __hash__(self) -> int:
        return hash(self.text_repr())

class VarType:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other) -> bool:
        return self is other
        
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __hash__(self):
        State.throw_error("Can't get variable type runtime representation")

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
        return "[" + str(_type.len) + "] " + type_to_str(_type.typ) 
    elif isinstance(_type, Struct):
        return _type.name
    elif isinstance(_type, VarType):
        return _type.name
    elif _type is None:
        return "any"
    else:
        assert False, f"Unimplemented type in type_to_str: {_type}"

def parse_type(token: tuple[str, str], error: str, auto_ptr: bool = True, allow_unpack: bool = False, 
               end: str | None = None, throw_exc: bool = True, var_type_scope: Optional[dict[str, VarType]] = None):
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
        return Ptr(parse_type((token[0][1:], token[1]), error, auto_ptr, allow_unpack, var_type_scope=var_type_scope))
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
        arr = Array(length, parse_type(next(State.tokens), error, True, False, end, var_type_scope=var_type_scope))
        if arr is None:
            if throw_exc:
                State.throw_error("array type was not defined")
            else:
                return None
        return Ptr(arr) if auto_ptr else arr
    else:
        if name in State.var_types():
            return State.var_types()[name]
        else:
            if var_type_scope is not None:
                var_type = VarType(name)
                var_type_scope[name] = var_type
                return var_type
            elif throw_exc:
                State.throw_error(f"Unknown type \"{name}\" in {error}")

def sizeof(_type) -> int:
    if isinstance(_type, Int) or isinstance(_type, Ptr) or isinstance(_type, Addr):
        return 8
    elif isinstance(_type, Struct):
        return sum([sizeof(field) for field in _type.fields_types])
    elif isinstance(_type, Array):
        return _type.len * sizeof(_type.typ)
    elif isinstance(_type, VarType):
        State.throw_error("Can't get size of type variable")
    elif _type is None:
        State.throw_error("Cant get size of any")
    else:
        assert False, f"Unimplemented type in sizeof: {type_to_str(_type)}"
    
    return 0 # Mypy, shut up!

def must_ptr(_type) -> bool:
    return isinstance(_type, Struct) or isinstance(_type, Array)


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
    if isinstance(exp, Ptr) and isinstance(got, Ptr):
        return check_varient(got.typ, exp.typ) or exp.typ is None or got.typ is None
    if isinstance(exp, Array) and isinstance(got, Array):
        return check_varient(got.typ, exp.typ) or exp.typ is None or got.typ is None
    if isinstance(exp, Struct) and isinstance(got, Struct):
        # equal is covariant
        return got == exp or check_contravariant(got, exp)
    if got == exp:
        return True

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