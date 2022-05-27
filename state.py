from dataclasses import dataclass
from enum import Enum, auto


class BlockType(Enum):
    IF = auto()
    ELSE = auto()

@dataclass
class Block:
    type: BlockType
    start: int
    end: int = -1


class State:
    block_stack: list[Block] = []
    current_ip: int = -1 

    @staticmethod
    def get_new_ip():
        State.current_ip += 1
        return State.current_ip