from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional

from state import State, Proc, cont_assert


class Type(ABC):
    @abstractmethod
    def __eq__(self, other) -> bool: ...

    @abstractmethod
    def text_repr(self) -> str: ...

    def __hash__(self) -> int:
        return hash(self.text_repr())


class Ptr(Type):
    def __init__(self, typ: Optional[Type] = None):
        self.typ = typ

    def __eq__(self, other) -> bool:
        if isinstance(other, Ptr):
            return self.typ == other.typ or other.typ is None or self.typ is None
        
        return False

    def text_repr(self) -> str:
        return f"ptr{'_' + self.typ.text_repr() if self.typ is not None else ''}"


class Array(Type):
    def __init__(self, len: int = -1, typ: Optional[Type] = None):
        self.len = len
        self.typ = typ

    def __eq__(self, other) -> bool:
        if isinstance(other, Array):
            return (
                (
                    self.typ == other.typ and\
                    self.len == other.len or -1 in (self.len, other.len)
                ) or\
                other.typ is None or\
                self.typ is None
            )
        return False

    def text_repr(self) -> str:
        cont_assert(self.typ is not None, 
            "Can't get text representation of an internal array")
        return f"arr_{self.typ.text_repr()}_{self.len}"


class Int(Type):
    def __eq__(self, other) -> bool:
        return isinstance(other, Int) or other is None

    def text_repr(self) -> str:
        return f"int"


class Addr(Type):
    def __eq__(self, other) -> bool:
        return isinstance(other, Addr) or other is None

    def text_repr(self) -> str:
        return f"addr"


class VarType(Type):
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other) -> bool:
        return self is other

    def text_repr(self) -> str:
        State.throw_error("Can't get variable type runtime representation")
        return "unreachable"


class Struct(Type):
    def __init__(
        self,
        name: str,
        fields: Dict[str, object],
        fields_types: List[object],
        parent: Optional["Struct"],
        defaults: Dict[int, int],
        is_unpack: bool,
    ):
        self.name: str = name
        self.fields: Dict[str, object] = {**fields, **(parent.fields if parent else {})}
        self.fields_types: List[object] = [*fields_types, *(parent.fields_types if parent else {})]
        self.is_unpackable: bool = is_unpack
        self.methods: Dict[str, Proc] = {} if parent is None else parent.methods.copy()
        self.parent: Optional["Struct"] = parent
        self.children: List["Struct"] = []
        self.defaults: Dict[int, int] = defaults
        self.static_methods: Dict[str, Proc] = {}

    def add_method(self, method: Proc):
        self.methods[method.name] = method
        for i in self.children:
            i.add_method(method)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Struct):
            return False
        if self is other:
            return True
        curr: Optional[Struct] = self
        while curr is not None:
            curr = curr.parent
            if curr is other:
                return True
        return False

    def text_repr(self) -> str:
        return f"struct_{id(self)}"


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
        cont_assert(False, f"Unimplemented type in type_to_str: {_type}")


def parse_type(
    token: Tuple[str, str],
    error: str,
    auto_ptr: bool = True,
    allow_unpack: bool = False,
    end: Optional[str] = None,
    throw_exc: bool = True,
    var_type_scope: Optional[Dict[str, VarType]] = None,
):
    State.loc = f"{State.filename}:{token[1]}"
    name = token[0]
    if end is not None:
        if end in name:
            end_index = name.find(end)
            State.tokens_queue.append((name[end_index + len(end):], token[1]))
            name = name[:end_index]
            if not name.strip():
                return None
    if name.startswith("*"):
        return Ptr(
            parse_type(
                (token[0][1:], token[1]), error,
                auto_ptr, allow_unpack,
                var_type_scope=var_type_scope,
            )
        )
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
            assert not throw_exc, f'structure "{name[1:]}" was not found'
            return None
        return State.structures[name[1:]].fields_types
    elif name.startswith("[") and name.endswith("]"):
        if name[1:-1] in State.constants:
            length = State.constants[name[1:-1]]
        elif name[1:-1].isnumeric():
            length = int(name[1:-1])
        else:
            assert not throw_exc, f'constant "{name[1:-1]}" was not found'
            return None
        arr = Array(
            length,
            parse_type(
                next(State.tokens), error,
                True, False, end,
                var_type_scope=var_type_scope,
            ),
        )
        if arr is None:
            assert not throw_exc, "array type was not defined"
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
            assert not throw_exc, f'Unknown type "{name}" in {error}'


def sizeof(_type) -> int:
    if isinstance(_type, Int) or isinstance(_type, Ptr) or isinstance(_type, Addr):
        return 8
    elif isinstance(_type, Struct):
        return sum([sizeof(field) for field in _type.fields_types])
    elif isinstance(_type, Array):
        return _type.len * sizeof(_type.typ)
    elif isinstance(_type, VarType):
        State.throw_error("Can't get size of a type variable")
    elif _type is None:
        State.throw_error("Can't get size of any")
    else:
        cont_assert(False, f"Unimplemented type in sizeof: {type_to_str(_type)}")


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
