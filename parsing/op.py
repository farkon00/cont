from enum import Enum, auto

class OpType(Enum):
    PUSH_INT = auto()
    OPERATOR = auto()

class Operator(Enum):
    ADD = auto()
    SUB = auto()
    MUL = auto()
    PRINT = auto()

class Op:
    def __init__(self, type: auto, operand) -> None:
        self.type: auto = type
        self.operand = operand 