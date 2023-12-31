import sys

from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Tuple, Set, Optional, Union
from enum import Enum, auto
from functools import reduce

from parsing.op import Op


class InternalAssertionError(Exception):
    """Error used in case there is an assertion needed in cont"""

def cont_assert(condition: bool, message: str):
    """Raise InternalAssertionError with the provided `message` if the `condition` is true"""
    if not condition:
        raise InternalAssertionError(message)


class BlockType(Enum):
    """The type of a `Block`"""
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    PROC = auto()
    BIND = auto()


@dataclass
class Block:
    """A block in code, which should be used for all the blocks in the `BlockType` enum."""
    type: BlockType
    start: int
    end: int = -1
    stack_effect: Optional[Union[Tuple[int, int], Tuple[int, int, int, int]]] = None
    binded: int = 0

@dataclass
class Route:
    type: str
    initial_stack: List["Type"]
    does_skip: bool = False # For break and continue
    do_other_branches_skip: List[bool] = field(default_factory=lambda: [])

    def make_with_patch(self, type: Optional[str] = None,
                        initial_stack: Optional[List["Type"]] = None,
                        does_skip: Optional[bool] = None,
                        do_other_branches_skip: Optional[List[bool]] = None) -> "Route":
        """
        Makes a new route with the values of the old one,
        changed as indicated by the arguments.
        
        Returns the route.
        """
        new_type = type if type is not None else self.type
        new_initial_stack = initial_stack if initial_stack is not None else self.initial_stack
        new_does_skip = does_skip if does_skip is not None else self.does_skip
        new_do_other_branches_skip = (do_other_branches_skip
            if do_other_branches_skip is not None
            else self.do_other_branches_skip)
        return Route(type=new_type, initial_stack=new_initial_stack,
                     does_skip=new_does_skip, do_other_branches_skip=new_do_other_branches_skip)

@dataclass
class Memory:
    """A memory defined with `memo` or `memory` keyword"""
    name: str
    offset: int

    global_offset = 0 # NOTE: The field doesn't have an annotation, so it's a static one

    @staticmethod
    def new_memory(name: str, size: int) -> "Memory":
        """
        Defines a new local or global memory depending on the `State`.
        Computes the offset of the memory and modifies `Memory.lobal_offset` if needed
        """
        if State.current_proc is None:
            mem = Memory(name, Memory.global_offset)
            Memory.global_offset += size + (8 - size % 8 if size % 8 != 0 else 0)
            State.memories[name] = mem
        else:
            mem = Memory(name, State.current_proc.memory_size)
            State.current_proc.memory_size += size + (
                8 - size % 8 if size % 8 != 0 else 0
            )
            State.current_proc.memories[name] = mem
        return mem


class Proc:
    """
    A procedure either defined in cont code or imported from an external source.
    Whether it was imported is denoted by is_imported, which might make some fields None if it's True.
    """
    def __init__(
        self, name: str, ip: int, in_stack: List["Type"],
        out_stack: List["Type"], block: Block, is_named: bool,
        is_self_named: bool, owner=None
    ):
        cont_assert(not (is_named and is_self_named), "Procedure cannot be both self-named and named.")

        self.name: str = name
        self.ip: int = ip
        self.owner: "Struct" = None if owner is None else owner.typ
        self.in_stack: List[object] = in_stack + ([owner] if owner is not None else [])
        self.out_stack: List[object] = out_stack
        self.block: Block = block
        
        self.is_named: bool = is_named
        self.is_self_named: bool = is_self_named
        self.is_imported: bool = False
        self.is_exported: bool = False

        self.memories: Dict[str, Memory] = {}
        self.memory_size: int = 0
        self.variables: Dict[str, "Type"] = {}  # type: ignore

        self.used_procs: Set[Proc] = set()

        if owner is not None:
            owner.typ.add_method(self)

    @classmethod
    def create_imported(cls, name: str, in_stack: List["Type"], out_stack: List["Type"]) -> "Proc":
        """Creates and returns a new Proc, which was imported from an external source."""
        self = cls.__new__(cls)

        self.name = name
        self.ip = State.get_new_ip(None)
        self.in_stack = in_stack
        self.out_stack = out_stack
        self.block: Block = None
        
        self.is_exported: bool = False
        self.is_named: bool = False
        self.is_self_named: bool = False
        self.is_imported: bool = True
        self.is_exported: bool = False

        self.memories: Dict[str, Memory] = {}
        self.memory_size: int = 0
        self.variables: Dict[str, "Type"] = {}  # type: ignore

        self.used_procs: Set[Proc] = set()

        return self
    
    def __str__(self) -> str:
        return f"Proc({self.name}, {None if self.owner is None else self.owner.name})"

    def __hash__(self) -> int:
        return id(self)


class StateSaver:
    """
    A class used for storing certain state from the `State` class, while parsing included modules.
    The constructor will load in the fields automatically.
    """
    def __init__(self):
        self.block_stack = State.block_stack
        self.tokens = State.tokens
        self.tokens_queue = State.tokens_queue
        self.loc = State.loc

    def load(self):
        """Loads the stored fields back into the `State` class"""
        State.block_stack = self.block_stack
        State.tokens = self.tokens
        State.tokens_queue = self.tokens_queue
        State.loc = self.loc


class State:
    @classmethod
    def initialize(cls):
        """Sets all the static fields to their default values"""
        cls.config: Any = None

        cls.block_stack: List[Block] = []
        cls.route_stack: List[Route] = []
        cls.bind_stack: list = []
        cls.do_stack: List[List[Op]] = []
        cls.bind_stack_size: int = 0
        cls.compile_ifs_opened: int = 0
        cls.false_compile_ifs: int = 0
        # This is used for the let keyowrd to unbind in the end, becuase main can be called multiple times on wat64
        cls.global_binded: int = 0

        cls.memories: Dict[str, Memory] = {}
        cls.variables: Dict[str, "Type"] = {}  # type: ignore
        cls.procs: Dict[str, Proc] = {}
        cls.imported_procs: List[Tuple[str, str]] = []
        cls.referenced_procs: Set[Proc] = set() # The procedures, which were used for proc pointers
        cls.structures: Dict[str, "Struct"] = {}  # type: ignore
        cls.constants: Dict[str, int] = {}
        cls.enums: Dict[str, List[str]] = {}
        cls.var_type_scopes: List[Dict[str, "VarType"]] = []  # type: ignore

        cls.used_procs: Set[Proc] = set()
        cls.included_files: List[str] = []
        cls.runtimed_types_set: Set["Type"] = set()  # type: ignore
        cls.runtimed_types_list: List["Type"] = []  # type: ignore
        cls.curr_type_id: int = 3

        cls.string_data: List[bytes] = []
        cls.locs_to_include: List[str] = []

        cls.tokens: Generator = (i for i in ())  # type: ignore
        cls.tokens_queue: List[Tuple[str, str]] = []
        cls.ops_by_ips: List[Op] = []

        cls.is_unpack = False
        cls.is_init = False
        cls.is_static = False
        cls.is_named = False

        cls.owner: Optional["Struct"] = None  # type: ignore

        cls.loc: str = ""
        cls.filename: str = ""
        cls.abs_path: str = ""

        cls.current_ip: int = -1
        cls.current_proc: Optional[Proc] = None

        cls.dir: str = ""

    @classmethod
    def full_reset(cls):
        """Resets the state to the default values including the static state of other classes."""
        cls.initialize()
        Memory.global_offset = 0

    UNAVAILABLE_NAMES: List[str] = [
        "if", "else", "end", "while", "proc", "bind", 
        *["syscall" + str(i) for i in range(7)], 
        "+", "-", "*", "div", "dup", "drop", "swap", "rot",
        "<", ">", "<=", ">=", "==", "!=", "!", "!8", "@", 
        "@8"
    ]

    ONE_RETURN_DUNDER_METHODS: List[str] = [
        "__add__", "__sub__", "__mul__", "__gt__", "__lt__", "__ge__", "__le__", "__eq__", "__ne__"
    ]
    NOT_SAME_TYPE_DUNDER_METHODS: List[str] = ["__index__", "__index_ptr__"]
    DUNDER_NEGATION_MAP: Dict[str, str] = {
        "__eq__" : "__ne__",
        "__gt__" : "__le__",
        "__lt__" : "__ge__",
    }
    for from_, to in DUNDER_NEGATION_MAP.copy().items():
        DUNDER_NEGATION_MAP[to] = from_

    TYPE_STRUCTS: List[str] = ["Type", "PtrType", "ArrayType", "AddrType", "Struct"]
    TYPE_IDS: Dict[str, int] = {
        "int" : 0,
        "ptr" : 1,
        "array" : 2,
        "addr" : 3,
    }

    def var_types() -> Dict[str, "VarType"]:  # type: ignore
        """Returns the union of all dictionaries in `State.var_type_scopes`"""
        if State.var_type_scopes:
            return reduce(lambda a, b: {**a, **b}, State.var_type_scopes)
        return {}

    @staticmethod
    def get_new_ip(op: Op):
        """
        Gets the next available instruction position for the op and
        performs all the state changes required.
        """
        State.current_ip += 1
        State.ops_by_ips.append(op)
        return State.current_ip

    @staticmethod
    def check_name(token: Tuple[str, str], error="procedure"):
        """
        Checks whether the provided token has a value, that is an available and valid name.

        Throws an error if it isn't. The `error` parameter indicates what was the type of the thing,
        that was supposed be named with the provided name e. g. a procedure.
        """
        if token[0] in [*State.procs, *State.memories, 
            *State.constants, *State.structures, *State.enums]:
            State.loc = token[1]
            State.throw_error(f'name for {error} "{token[0]}" is already taken')
        if token[0] in State.UNAVAILABLE_NAMES:
            State.loc = token[1]
            State.throw_error(f'name for {error} "{token[0]}" is unavailable')

    @staticmethod
    def get_proc_by_block(block: Block):
        """
        Gets the `Proc` object for the procedure, that uses the block `Block`.
        If such a procedure is not found an exception will be raised.
        """
        proc_op = State.ops_by_ips[block.start]
        return proc_op.operand

    @staticmethod
    def throw_error(error: str, do_exit: bool = True):
        """
        Throws a cont error with all the formatting.
        The `State.loc` will be used for the location of the error.

        If `do_exit` is false the message will be printed to stderr, but the script won't exit.
        """
        sys.stderr.write(f"\033[1;31mError {State.loc}:\033[0m {error}\n")
        if do_exit:
            exit(1)

    @staticmethod
    def add_proc_use(proc):
        """Modifies the directed graph of procedures usage according to the state"""
        if State.current_proc is None:
            State.used_procs.add(proc)
        else:
            State.current_proc.used_procs.add(proc)

    @staticmethod
    def compute_used_procs():
        """Modifies `State.used_procs` to include every single procedure, that should be compiled."""
        orig = State.used_procs.copy()
        State.used_procs = set()
        for i in orig:
            State.used_procs.add(i)
            State._compute_used_procs(i)

    @staticmethod
    def _compute_used_procs(proc: Proc):
        """A helper method for `State.compute_used_procs`"""
        for i in proc.used_procs:
            if i in State.used_procs:
                continue
            State.used_procs.add(i)
            State._compute_used_procs(i)

    @staticmethod
    def is_hex(token: str) -> bool:
        """
        A utils method, which determines whether a given string is a valid hex number.
        The method does not need any prefixes.
        
        The token of "05aF" will result in a True, meanwhile "0xa0" will result in a False. 
        """
        return all(i.lower() in "abcdef1234567890" for i in token)

    @staticmethod
    def is_bin(token: str) -> bool:
        """
        A utils method, which determines whether a given string is a valid binary number.
        The method does not need any prefixes.
        
        The token of "0001010" will result in a True, meanwhile "0b110" will result in a False. 
        """
        return all(i.lower() in "01" for i in token)

    @staticmethod
    def is_oct(token: str) -> bool:
        """
        A utils method, which determines whether a given string is a valid octal number.
        The method does not need any prefixes.
        
        The token of "163" will result in a True, meanwhile "0o120" will result in a False. 
        """
        return all(i.lower() in "01234567" for i in token)

State.initialize()