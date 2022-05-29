from enum import Enum, auto

class OpType(Enum):
    PUSH_INT = auto()
    PUSH_MEMORY = auto()
    PUSH_STR = auto()
    IF = auto()
    ELSE = auto()
    ENDIF = auto()
    WHILE = auto()
    ENDWHILE = auto()
    DEFPROC = auto()
    ENDPROC = auto()
    CALL = auto()
    SYSCALL = auto()
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
    CAST_INT = auto()
    CAST_PTR = auto()
    PRINT = auto()

class Op:
    def __init__(self, type: OpType, operand, loc: str = "") -> None:
        self.type: OpType = type
        self.operand = operand 
        self.loc: str = loc