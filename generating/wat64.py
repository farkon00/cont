from typing import List
from parsing.op import *
from state import *

def compile_ops_wat64(ops: List[Op]):
    generate_wat64(ops)

def generate_wat64(ops: List[Op]):
    cont_assert(False, "Not implemented")