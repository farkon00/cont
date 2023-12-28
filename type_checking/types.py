from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional

from state import State, Proc, cont_assert


class Type(ABC):
    """An abstract class for all cont types"""
    def __hash__(self) -> int:
        return hash(self.text_repr())

    @abstractmethod
    def __eq__(self, other) -> bool: ...

    @abstractmethod
    def text_repr(self) -> str: ...


class Ptr(Type):
    """
    A cont pointer type, where `typ` is the type the pointer to pointing to
    or None if the pointer is `ptr`.
    """
    def __init__(self, typ: Optional[Type] = None):
        self.typ = typ

    def __eq__(self, other) -> bool:
        if isinstance(other, Ptr):
            return self.typ == other.typ or other.typ is None or self.typ is None
        
        return False

    def text_repr(self) -> str:
        return f"ptr{'_' + self.typ.text_repr() if self.typ is not None else ''}"
    
    def __hash__(self) -> int:
        return hash(self.text_repr())


class Array(Type):
    """
    A cont array type, where `typ` is the type of the elements and `len` is the length.

    Cannot exist on the stack, but Ptr(Array(...)) can. The `typ` has
    to have a size of 8 bytes.

    `typ` can be None and `len` can be -1, but such a type can only be
    created internally in the language and cannot be used for certain operations
    with types. If `typ` is None, that means an array with any type of element.
    And if `len` is -1 it means an array with any length.
    """
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

    def __hash__(self) -> int:
        return hash(self.text_repr())


class Int(Type):
    """A cont integer type"""
    def __eq__(self, other) -> bool:
        return isinstance(other, Int) or other is None

    def text_repr(self) -> str:
        return f"int"

    def __hash__(self) -> int:
        return hash(self.text_repr())


class Addr(Type):
    """
    A cont address type, denotes a function pointer. Has `in_types` and
    `out_types` which must match for addrs to be equal.
    """
    def __init__(self, in_types: List[Type], out_types: List[Type]):
        self.in_types = in_types
        self.out_types = out_types

    def __eq__(self, other) -> bool:
        if other is None: return True
        if not isinstance(other, Addr): return False
        return self.in_types == other.in_types and self.out_types == other.out_types

    def text_repr(self) -> str:
        in_types = '__'.join([i.text_repr() for i in self.in_types])
        out_types = '__'.join([i.text_repr() for i in self.out_types])
        return f"addr_{len(self.in_types)}_{len(self.out_types)}__{in_types}___{out_types}"

    def __hash__(self) -> int:
        return hash(self.text_repr())


class VarType(Type):
    """
    A cont variable type, can only be created in a function signature and
    has to be replaced by a concrete type on every call.
    """
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other) -> bool:
        return self is other

    def text_repr(self) -> str:
        State.throw_error("Can't get variable type runtime representation")
        return "unreachable"

    def __hash__(self) -> int:
        return hash(self.text_repr())


class Struct(Type):
    """
    A cont structure. Used both as a type and as a container for storing data about the struct.
    
    Cannot exist on the stack, but Ptr(Struct(...)) can.
    The types of fields have to be 8 bytes in length.
    """
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
        self.static_methods: Dict[str, Proc] = {} if parent is None else parent.static_methods.copy()

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

    def __hash__(self) -> int:
        return hash(self.text_repr())


def type_to_str(_type: Type) -> str:
    """
    Converts cont type object to a human-readable string
    """
    if isinstance(_type, Int):
        return "int"
    elif isinstance(_type, Addr):
        in_types = " ".join([type_to_str(i) for i in _type.in_types])
        out_types = " ".join([type_to_str(i) for i in _type.out_types])
        return f"addr ({in_types} -> {out_types})"
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
    """
    Parses a cont type from a token. If parsing fails throws an error
    if throw_exc is set to True. Might use the global token iterator to get more tokens
    for a type if needed.

    * `token` is the first token of the type to be parsed
    * `error` is the context in which the type is being parsed e. g. a procedure contract
    * `auto_ptr` is a flag, which determines if the types, that cannot exist on the stack
    e. g. structs or array should be wrapper in a pointer
    * `allow_unpack` is a flag, which determines if type unpacking is allowed in the current context
    (a list of types will be returned if there is going to be unpacking and this flag is set)
    * `end` is a string, which will end the current context
    * `throw_exc` is a flag, which determines if the function should throw cont errors if parsing fails
    * `var_type_scope` is the newest type variable scope, where the new variables are going to be added to
    (this argument not being None indicates, that the caller wants an ability for new type variables to be declared)
    """
    # TODO: figure out if some asserts not checking for throw_exc is the intended behavior
    State.loc = token[1]
    og_name = name = token[0]
    is_ended = False
    if end is not None:
        if end in name:
            end_index = name.find(end)
            if name[end_index + len(end):]:
                State.tokens_queue.append((name[end_index + len(end):], token[1]))
            name = name[:end_index]
            if not name.strip():
                return (True, None)
    if name.startswith("*"):
        result = Ptr(
            parse_type(
                (token[0][1:], token[1]), error,
                auto_ptr=auto_ptr, allow_unpack=False,
                var_type_scope=var_type_scope,
            )
        )
    elif name == "int":
        result = Int()
    elif name == "ptr":
        result = Ptr()
    elif name == "addr":
        assert end is None or end not in og_name, "Expected procedure name"
        try:
            name, loc = next(State.tokens)
        except StopIteration:
            State.throw_exception("Unexpected EOF")
        if end is not None:
            if end in name:
                end_index = name.find(end)
                if name[end_index + len(end):]:
                    State.tokens_queue.append((name[end_index + len(end):], loc))
                name = name[:end_index]
                State.loc = loc
                is_ended = True
                assert name, "Procedure name was not provided"
        assert name in State.procs, f"Procedure {name} was not found"
        proc = State.procs[name]
        result = Addr(proc.in_stack, proc.out_stack)
    elif name in State.structures:
        result = Ptr(State.structures[name]) if auto_ptr else State.structures[name]
    elif name.startswith("@") and allow_unpack:
        if name[1:] not in State.structures:
            assert not throw_exc, f'structure "{name[1:]}" was not found'
            result = None
        else:
            result = State.structures[name[1:]].fields_types
    elif name.startswith("[") and name.endswith("]"):
        if name[1:-1] in State.constants:
            length = State.constants[name[1:-1]]
        elif name[1:-1].isnumeric():
            length = int(name[1:-1])
        else:
            assert not throw_exc, f'constant "{name[1:-1]}" was not found'
            length = None
            result = None
        if length is not None:
            assert end is None or end not in og_name, "Expected array type"
            try:
                arr_type_tok = next(State.tokens)
            except StopIteration:
                State.throw_error("Expected array type")
            if end is not None:
                is_ended, arr_type = parse_type(
                    arr_type_tok, error,
                    True, False, end,
                    var_type_scope=var_type_scope,
                )
            else:
                arr_type = parse_type(
                    arr_type_tok, error,
                    True, False, end,
                    var_type_scope=var_type_scope,
                )
            arr = Array(length, arr_type)
            if arr is None:
                assert not throw_exc, "array type was not defined"
                result = None
            else:
                result = Ptr(arr) if auto_ptr else arr
    elif name == "":
        State.throw_error(f"Expected token, but end was reached in {error}")
    else:
        if name in State.var_types():
            result = State.var_types()[name]
        else:
            if var_type_scope is not None:
                result = var_type = VarType(name)
                var_type_scope[name] = var_type
            else:
                assert not throw_exc, f'Unknown type "{name}" in {error}'
    if end is not None:
        return ((end is None or end in og_name) or is_ended, result)
    else:
        return result


def sizeof(_type: Optional[Type]) -> int:
    """
    Returns the size of a type. Will throw an error if
    the any type or a type variable was given.
    """
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


def must_ptr(_type: Optional[Type]) -> bool:
    """Returns True if the type cannot be present on the stack"""
    return isinstance(_type, Struct) or isinstance(_type, Array)


def down_cast(type1: Optional[Type], type2: Optional[Type]) -> Tuple[Optional[Type], bool]:
    """
    Finds a type, that matches both provided types.

    Returns a tuple of a type and a bool, the bool indicates
    whether the resulting type was found, the type is None if
    the bool is False. If the bool is True the resulting type is
    non-None unless one of the input types is None.
    """
    if type1 is None: return (type2, True)
    if type2 is None: return (type1, True)
    if isinstance(type1, Struct) and isinstance(type2, Struct):
        type1_parents = set([type1.name])
        curr_struct = type1
        while curr_struct.parent is not None:
            curr_struct = curr_struct.parent
            type1_parents.add(curr_struct.name)
        curr_struct = type2
        while curr_struct is not None:
            if curr_struct.name in type1_parents:
                return (curr_struct, True)
            curr_struct = curr_struct.parent
        return (None, False)
    if isinstance(type1, Ptr) and isinstance(type2, Ptr):
        if type1.typ is None or type2.typ is None:
            return (Ptr(None), True)
        typ, is_succ = down_cast(type1.typ, type2.typ)
        if not is_succ: return (None, False)
        return (Ptr(typ), True)
    if isinstance(type1, Array) and isinstance(type2, Array):
        if type1.len != type2.len: return (None, False)
        typ, is_succ = down_cast(type1.typ, type2.typ)
        if not is_succ: return (None, False)
        return (Array(type1.len, typ), True)
    if isinstance(type1, Addr) and isinstance(type2, Addr):
        if len(type1.in_types) != len(type2.in_types): return (None, False)
        if len(type1.out_types) != len(type2.out_types): return (None, False)
        in_types, out_types = [], []
        for i, j in zip(type1.in_types, type2.in_types):
            typ, is_succ = down_cast(i, j)
            if not is_succ: return (None, False)
            in_types.append(typ)
        for i, j in zip(type1.out_types, type2.out_types):
            typ, is_succ = down_cast(i, j)
            if not is_succ: return (None, False)
            out_types.append(typ)
        return (Addr(in_types, out_types), True)
    if type1 == type2:
        return (type2, True)
    if type2 == type1:
        return (type1, True)
    return (None, False)
