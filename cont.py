import sys
import os

from state import State, cont_assert
from config import Config
from parsing.parsing import parse_to_ops
from generating.generating import compile_ops
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
    State.dir = "."  # os.path.dirname(__file__)

    ops = parse_to_ops(program, config.dump_tokens)

    assert not State.compile_ifs_opened, "unclosed #if" 
    cont_assert(not State.false_compile_ifs, "Something went terribly wrong with #if")

    if config.dump:
        for op in ops:
            if op.compiled:
                print(
                    f"{op.loc} {op.type.name} {op.operand if op.type.name != 'OPERATOR' else op.operand.name}"
                )
        return

    type_check(ops, is_main=True)

    if config.dump_tc:
        for op in ops:
            if op.compiled:
                print(
                    f"{op.loc} {op.type.name} {op.operand if op.type.name != 'OPERATOR' else op.operand.name}"
                )
        return

    State.compute_used_procs()

    compile_ops(ops)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        State.throw_error(e.args[0])
