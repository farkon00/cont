from dataclasses import dataclass
import sys
from typing import Generator
from enum import Enum, auto


class BlockType(Enum):
    IF = auto()
    ELSE = auto()
    WHILE = auto()

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
        mem = Memory(name, Memory.global_offset)
        Memory.global_offset += size + (8 - size % 8 if size % 8 != 0 else 0)
        State.memories[name] = mem
        return mem

class State:
    block_stack: list[Block] = []
    route_stack: list[tuple[str, list[type]]] = []
    memories: dict[str, Memory] = {}
    
    tokens: Generator = (i for i in ()) # type: ignore

    loc: str = ""
    filename: str = ""
    current_ip: int = -1

    @staticmethod
    def get_new_ip():
        State.current_ip += 1
        return State.current_ip

    @staticmethod
    def throw_error(error: str, do_exit: bool = True):
        sys.stderr.write(f"\033[1;31mError {State.filename}:{State.loc}:\033[0m {error}\n")
        if do_exit:
            exit(1)