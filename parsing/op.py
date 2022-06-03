from enum import Enum, auto

class OpType(Enum):
    PUSH_INT = auto()
    PUSH_MEMORY = auto()
    PUSH_LOCAL_MEM = auto()
    PUSH_VAR = auto()
    PUSH_LOCAL_VAR = auto()
    PUSH_STR = auto()
    PUSH_NULL_STR = auto()
    CAST = auto()
    IF = auto()
    ELSE = auto()
    ENDIF = auto()
    WHILE = auto()
    ENDWHILE = auto()
    DEFPROC = auto()
    ENDPROC = auto()
    BIND = auto()
    PUSH_BIND_STACK = auto()
    UNBIND = auto()
    CALL = auto()
    PACK = auto()
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
    PRINT = auto()

class Op:
    def __init__(self, type: OpType, operand, loc: str = "") -> None:
        self.type: OpType = type
        self.operand = operand 
        self.loc: str = loc