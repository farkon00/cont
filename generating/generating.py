from typing import List
from parsing.op import *
from state import *
from .fasm_x86_64_linux import generate_fasm_x86_64_linux
from .wat64 import generate_wat64

TARGETS = {
    "fasm_x86_64_linux" : generate_fasm_x86_64_linux,
    "wat64" : generate_wat64
}

def generate(ops: List[Op]):
    cont_assert(State.config.target in TARGETS, "taget not found")

    return TARGETS[State.config.target](ops)