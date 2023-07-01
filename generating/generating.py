from typing import List
from parsing.op import *
from state import *
from .fasm_x86_64_linux import compile_ops_fasm_x86_64_linux
from .wat64 import compile_ops_wat64

TARGETS = {
    "fasm_x86_64_linux" : compile_ops_fasm_x86_64_linux,
    "wat64" : compile_ops_wat64
}

def compile_ops(ops: List[Op]):
    cont_assert(State.config.target in TARGETS, "taget not found")

    return TARGETS[State.config.target](ops)
