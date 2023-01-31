import subprocess
from typing import List

from parsing.op import *
from state import *

assert len(Operator) == 20, "Unimplemented operator in wat64.py"
assert len(OpType) == 40, "Unimplemented type in wat64.py"

def compile_ops_wat64(ops: List[Op]):
    if State.config.run:
        print("Can't use run flag for this target")
        exit(1)
    if subprocess.getstatusoutput("wat2wasm --version")[0] != 0:
        print("Please install wabt and wat2wasm specifically.")
        exit(1)
    
    out = State.filename if State.config.out is None else State.config.out

    with open(f"{out}.wat", "w") as f:
        f.write(generate_wat64(ops))

    subprocess.run(["wat2wasm", f"{out}.wat"], stdin=sys.stdin, stderr=sys.stderr)

def generate_wat64(ops: List[Op]):
    return \
        """
        (module
        (func (export "main") (param i64 i64) (result i64)
            local.get 0
            local.get 1
            i64.add))
        """ # Test code 
    cont_assert(False, "Not implemented")