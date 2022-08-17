import sys
import os
import subprocess

from state import State
from config import Config
from parsing.parsing import parse_to_ops
from generating.generating import generate_fasm
from type_checking.type_checking import type_check

def main():
    config = Config(sys.argv)
    State.config = config

    file_name = os.path.splitext(config.program)[0]

    with open(config.program, "r") as f:
        program = f.read() 

    sys.stdout = open(config.stdout, "w") if config.stdout else sys.stdout
    sys.stderr = open(config.error, "w") if config.error else sys.stderr
    sys.stdin = open(config.input, "r") if config.input else sys.stdin

    State.filename = file_name
    State.dir = os.path.dirname(__file__)

    ops = parse_to_ops(program, config.dump_tokens)

    if config.dump:
        for op in ops:
            if op.compiled:
                print(f"{op.loc} {op.type.name} {op.operand if op.type.name != 'OPERATOR' else op.operand.name}")
        return 

    type_check(ops)

    State.compute_used_procs()

    out = file_name if config.out is None else config.out

    with open(f"{out}.asm", "w") as f:
        f.write(generate_fasm(ops))

    subprocess.run(["fasm", f"{out}.asm"], stdin=sys.stdin, stderr=sys.stderr)

    if config.run:
        subprocess.run([f"./{out}"], stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr)

if __name__ == "__main__":
    main()