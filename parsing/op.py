from enum import Enum, auto

class OpType(Enum):
    PUSH_INT = auto()
    OPERATOR = auto()

class Operator(Enum):
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    DUP = auto()
    DROP = auto()
    SWAP = auto()
    ROT = auto()
    PRINT = auto()

class Op:
    def __init__(self, type: OpType, operand) -> None:
        self.type: OpType = type
        self.operand = operand 