import sys

from dataclasses import dataclass
from typing import List, Tuple, Dict, Set, Optional, Any, Generator
from enum import Enum, auto
from functools import reduce

from parsing.op import Op


class InternalAssertionError(Exception):
    """
    Error used in case there is assertion needed in cont
    """
    pass

def cont_assert(condition: bool, message: str):
    if not condition:
        raise InternalAssertionError(message)


class BlockType(Enum):
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    PROC = auto()
    BIND = auto()


@dataclass
class Block:
    type: BlockType
    start: int
    end: int = -1
    stack_effect: Optional[Tuple[int, int]] = None

@dataclass
class Memory:
    name: str
    offset: int

    global_offset = 0

    @staticmethod
    def new_memory(name: str, size: int) -> "Memory":
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
    def __init__(self):
        self.block_stack = State.block_stack
        self.tokens = State.tokens
        self.tokens_queue = State.tokens_queue
        self.loc = State.loc

    def load(self):
        State.block_stack = self.block_stack
        State.tokens = self.tokens
        State.tokens_queue = self.tokens_queue
        State.loc = self.loc


class State:
    config: Any = None

    block_stack: List[Block] = []
    route_stack: List[Tuple[str, List["Type"]]] = []  # type: ignore
    bind_stack: list = []
    do_stack: List[List[Op]] = []
    bind_stack_size: int = 0
    compile_ifs_opened: int = 0
    false_compile_ifs: int = 0

    memories: Dict[str, Memory] = {}
    variables: Dict[str, "Type"] = {}  # type: ignore
    procs: Dict[str, Proc] = {}
    imported_procs: List[Tuple[str, str]] = []
    referenced_procs: Set[Proc] = set() # The procedures, which were used for proc pointers
    structures: Dict[str, "Struct"] = {}  # type: ignore
    constants: Dict[str, int] = {}
    enums: Dict[str, List[str]] = {}
    var_type_scopes: List[Dict[str, "VarType"]] = []  # type: ignore

    used_procs: Set[Proc] = set()
    included_files: List[str] = []
    runtimed_types_set: Set["Type"] = set()  # type: ignore
    runtimed_types_list: List["Type"] = []  # type: ignore
    curr_type_id: int = 3

    string_data: List[bytes] = []
    locs_to_include: List[str] = []

    tokens: Generator = (i for i in ())  # type: ignore
    tokens_queue: List[Tuple[str, str]] = []
    ops_by_ips: List[Op] = []

    is_unpack = False
    is_init = False
    is_static = False
    is_named = False

    owner: Optional["Struct"] = None  # type: ignore

    loc: str = ""
    filename: str = ""

    current_ip: int = -1
    current_proc: Optional[Proc] = None

    dir: str = ""

    UNAVAILABLE_NAMES: List[str] = [
        "if", "else", "end", "while", "proc", "bind", 
        *["syscall" + str(i) for i in range(7)], 
        "+", "-", "*", "div", "dup", "drop", "swap", "rot",
        "<", ">", "<=", ">=", "==", "!=", "!", "!8", "@", 
        "@8"
    ]

    DUNDER_METHODS: List[str] = [
        "__add__", "__sub__", "__mul__", "__gt__", "__lt__", "__ge__", "__le__", "__eq__", "__ne__"
    ]
    NOT_SAME_TYPE_DUNDER_METHODS: List[str] = ["__index__", "__index_ptr__"]

    TYPE_STRUCTS: List[str] = ["Type", "PtrType", "ArrayType", "AddrType", "Struct"]
    TYPE_IDS: Dict[str, int] = {
        "int" : 0,
        "ptr" : 1,
        "array" : 2,
        "addr" : 3,
    }

    def var_types() -> Dict[str, "VarType"]:  # type: ignore
        if State.var_type_scopes:
            return reduce(lambda a, b: {**a, **b}, State.var_type_scopes)
        return {}

    @staticmethod
    def get_new_ip(op: Op):
        State.current_ip += 1
        State.ops_by_ips.append(op)
        return State.current_ip

    @staticmethod
    def check_name(token: Tuple[str, str], error="procedure"):
        if token[0] in [*State.procs, *State.memories, 
            *State.constants, *State.structures, *State.enums]:
            State.loc = token[1]
            State.throw_error(f'name for {error} "{token[0]}" is already taken')
        if token[0] in State.UNAVAILABLE_NAMES:
            State.loc = token[1]
            State.throw_error(f'name for {error} "{token[0]}" is unavailable')

    @staticmethod
    def get_proc_by_block(block: Block):
        proc_op = State.ops_by_ips[block.start]
        return proc_op.operand

    @staticmethod
    def throw_error(error: str, do_exit: bool = True):
        sys.stderr.write(f"\033[1;31mError {State.loc}:\033[0m {error}\n")
        if do_exit:
            exit(1)

    @staticmethod
    def add_proc_use(proc):
        if State.current_proc is None:
            State.used_procs.add(proc)
        else:
            State.current_proc.used_procs.add(proc)

    @staticmethod
    def compute_used_procs():
        orig = State.used_procs.copy()
        State.used_procs = set()
        for i in orig:
            State.used_procs.add(i)
            State._compute_used_procs(i)

    @staticmethod
    def _compute_used_procs(proc: Proc):
        for i in proc.used_procs:
            if i in State.used_procs:
                continue
            State.used_procs.add(i)
            State._compute_used_procs(i)

    @staticmethod
    def is_hex(token: str) -> bool:
        return all(i.lower() in "abcdef1234567890" for i in token)

    @staticmethod
    def is_bin(token: str) -> bool:
        return all(i.lower() in "01" for i in token)

    @staticmethod
    def is_oct(token: str) -> bool:
        return all(i.lower() in "01234567" for i in token)
