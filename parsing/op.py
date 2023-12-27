from enum import Enum, auto


class OpType(Enum):
    """An enum with types of operations"""
    PUSH_INT = auto()
    PUSH_MEMORY = auto()
    PUSH_LOCAL_MEM = auto()
    PUSH_VAR = auto()
    PUSH_LOCAL_VAR = auto()
    PUSH_VAR_PTR = auto()
    PUSH_LOCAL_VAR_PTR = auto()
    PUSH_STR = auto()
    PUSH_NULL_STR = auto()
    PUSH_PROC = auto()
    CAST = auto()
    IF = auto()
    ELSE = auto()
    ENDIF = auto()
    WHILE = auto()
    ENDWHILE = auto()
    FOR = auto()
    ENDFOR = auto()
    DEFPROC = auto()
    ENDPROC = auto()
    BIND = auto()
    PUSH_BIND_STACK = auto()
    UNBIND = auto()
    CALL = auto()
    TYPED_LOAD = auto()
    PACK = auto()
    UNPACK = auto()
    PUSH_FIELD = auto()
    PUSH_FIELD_PTR = auto()
    MOVE_STRUCT = auto()
    UPCAST = auto()
    CALL_ADDR = auto()
    INDEX = auto()
    INDEX_PTR = auto()
    AUTO_INIT = auto()
    SIZEOF = auto()
    SYSCALL = auto()
    PUSH_TYPE = auto()
    ASM = auto()
    OPERATOR = auto()


class Operator(Enum):
    """An enum with sub-types of operations with type OpType.OPERATOR"""
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    DUP = auto()
    DROP = auto()
    SWAP = auto()
    ROT = auto()
    OVER = auto()
    LT = auto()
    GT = auto()
    EQ = auto()
    LE = auto()
    GE = auto()
    NE = auto()
    STORE = auto()
    STRONG_STORE = auto()
    STORE8 = auto()
    LOAD = auto()
    LOAD8 = auto()


class Op:
    """An operation"""
    def __init__(self, type: OpType, operand=None, loc: str = "", loc_id=-1) -> None:
        self.type: OpType = type
        self.operand = operand
        self.loc: str = loc
        self.loc_id: int = loc_id
        self.compiled: bool = True

    def copy(self):
        """Creates a new `Op` object, that has all the same data except the loc_id."""
        op = Op(self.type, self.operand, self.loc)
        op.compiled = self.compiled
        return op
