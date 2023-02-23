import sys
import os
import stat
import subprocess

from state import State, cont_assert
from config import Config
from parsing.op import OpType
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

    assert not State.compile_ifs_opened, "unclosed #if" 
    cont_assert(not State.false_compile_ifs, "Something went terribly wrong with #if")

    if config.dump_proc is not None:
        if config.dump_proc in State.procs:
            proc = State.procs[config.dump_proc]
        elif "." in config.dump_proc:
            parts = config.dump_proc.split(".", 1)
            if parts[0] not in State.structures:
                sys.stderr.write(f"\033[1;31mError:\033[0m Incorrect procedure name for dump_proc\n")
                exit(1)
            struct = State.structures[parts[0]]
            if parts[1] in struct.methods:
                proc = struct.methods[parts[1]]
            elif parts[1] in struct.static_methods:
                proc = struct.static_methods[parts[1]]
            else:
                sys.stderr.write(f"\033[1;31mError:\033[0m Incorrect procedure name for dump_proc\n")
                exit(1)   
        else:
            sys.stderr.write(f"\033[1;31mError:\033[0m Incorrect procedure name for dump_proc\n")
            exit(1)
        proc_op = State.ops_by_ips[proc.ip]
        is_printing = False
        for op in ops:
            if op is proc_op:
                is_printing = True
            if is_printing:
                print(
                    f"{op.loc} {op.type.name} {op.operand if op.type.name != 'OPERATOR' else op.operand.name}"
                )
            if is_printing and op.type == OpType.ENDPROC:
                break
        exit(0)

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

    if subprocess.getstatusoutput("fasm -v")[0] == 0:
        print("Please install Flat Assembler (Fasm).")
        print("Use sudo apt install fasm if you are using Debian/Ubuntu")
        exit()

    out = file_name if config.out is None else config.out

    with open(f"{out}.asm", "w") as f:
        f.write(generate_fasm(ops))

    subprocess.run(["fasm", f"{out}.asm"], stdin=sys.stdin, stderr=sys.stderr)
    os.chmod(
        out, os.stat(out).st_mode | stat.S_IEXEC
    )  # Give execution permission to the file

    if config.run:
        subprocess.run(
            [f"./{out}"], stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr
        )


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        State.throw_error(e.args[0])
