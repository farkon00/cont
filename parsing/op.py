from enum import Enum, auto

class OpType(Enum):
    PUSH_INT = auto()
    PUSH_MEMORY = auto()
    IF = auto()
    ELSE = auto()
    ENDIF = auto()
    WHILE = auto()
    ENDWHILE = auto()
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
    LT = auto()
    GT = auto()
    EQ = auto()
    LE = auto()
    GE = auto()
    NE = auto()
    STORE = auto()
    STORE8 = auto()
    LOAD = auto()
    LOAD8 = auto() 
    PRINT = auto()

class Op:
    def __init__(self, type: OpType, operand) -> None:
        self.type: OpType = type
        self.operand = operand 