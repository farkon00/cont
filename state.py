from dataclasses import dataclass
import sys
from typing import Generator, Optional
from enum import Enum, auto

from parsing.op import Op, Operator


class BlockType(Enum):
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    PROC = auto()
    BIND = auto()


@dataclass
class Block:
    type: BlockType
    start: int
    end: int = -1


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
            State.current_proc.memory_size += size + (8 - size % 8 if size % 8 != 0 else 0)
            State.current_proc.memories[name] = mem
        return mem


class Proc:
    def __init__(self, name: str, ip: int, in_stack: list[object], out_stack: list[object], block: Block, owner=None):
        self.name: str = name
        self.ip: int = ip
        self.in_stack: list[object] = in_stack + ([owner] if owner is not None else []) 
        self.out_stack: list[object] = out_stack
        self.block: Block = block
        self.memories: dict[str, Memory] = {}
        self.memory_size : int = 0
        self.variables : dict[str, object] = {}
        
        if owner is not None:
            owner.typ.add_method(self)


class Struct:
    def __init__(self, name: str, fields: dict[str, object], fields_types: list[object],
                 parent: Optional["Struct"], defaults: dict[int, int]):
        self.name: str = name
        self.fields: dict[str, object] = fields
        self.fields_types: list[object] = fields_types
        self.is_unpackable: bool = State.is_unpack
        self.methods: dict[str, Proc] = {} if parent is None else parent.methods.copy()
        self.parent: "Struct" | None = parent
        self.children: list["Struct"] = []
        self.defaults: dict[int, int] = defaults
        self.static_methods: dict[str, Proc] = {}

    def add_method(self, method: Proc):
        self.methods[method.name] = method
        for i in self.children:
            i.add_method(method)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Struct):
            return False
        if self is other:
            return True
        curr: Struct | None = self
        while curr is not None:
            curr = curr.parent
            if curr is other:
                return True
        return False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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
    block_stack: list[Block] = []
    route_stack: list[tuple[str, list[type]]] = []
    bind_stack: list[str | type] = []
    do_stack: list[list[Op]] = []
    bind_stack_size: int = 0

    memories: dict[str, Memory] = {}
    variables: dict[str, object] = {} 
    procs: dict[str, Proc] = {}
    structures: dict[str, Struct] = {}
    constants: dict[str, int] = {}
    enums: dict[str, list[str]] = {}

    tokens: Generator = (i for i in ()) # type: ignore
    tokens_queue: list[tuple[str, str]] = []
    ops_by_ips: list[Op] = []

    is_string = False
    is_null = False
    is_unpack = False
    is_init = False
    is_static = False
    owner : Struct | None = None
    string_buffer: str = ""
    string_data: list[bytes] = [] 

    loc: str = ""
    filename: str = ""

    current_ip: int = -1
    current_proc: Proc | None = None

    dir: str = ""

    UNAVAILABLE_NAMES: list[str] = [
        "if", "else", "end", "while", "proc", "bind", 
        *["syscall" + str(i) for i in range(7)], 
        "+", "-", "*", "div", "dup", "drop", "swap", "rot",
        "<", ">", "<=", ">=", "==", "!=", "!", "!8", "@", 
        "@8"
    ]

    DUNDER_METHODS: list[str] = [
        "__add__", "__sub__", "__mul__", "__gt__", "__lt__", "__ge__", "__le__", "__eq__", "__ne__",
    ]

    @staticmethod
    def get_new_ip(op: Op):
        State.current_ip += 1
        State.ops_by_ips.append(op)
        return State.current_ip

    @staticmethod
    def check_name(token: tuple[str, str], error="procedure"):
        if token[0] in State.procs or token[0] in State.memories or\
           token[0] in State.constants or token[0] in State.structures or\
           token[0] in State.enums:
            State.loc = token[1]
            State.throw_error(f"name for {error} \"{token[0]}\" is already taken")
        if token[0] in State.UNAVAILABLE_NAMES:
            State.loc = token[1]
            State.throw_error(f"name for {error} \"{token[0]}\" is unavailable")

    @staticmethod
    def get_proc_by_block(block: Block):
        proc_op = State.ops_by_ips[block.start]
        return proc_op.operand

    @staticmethod
    def throw_error(error: str, do_exit: bool = True):
        sys.stderr.write(f"\033[1;31mError {State.loc}:\033[0m {error}\n")
        if do_exit:
            exit(1)