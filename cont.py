import subprocess
import sys
import os
import argparse

from state import State
from parsing.parsing import parse_to_ops
from generating.generating import generate_fasm
from type_checking.type_checking import type_check

def main():
    # Argv handeling

    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("program", help="The program to compile and optionally run")
    args_parser.add_argument("-o", "--out", default=None, dest="out", 
        help="The output executable file and name for .asm file")
    args_parser.add_argument("-r", "--run", action="store_true", default=False, dest="run", 
        help="Run program after compilation")
    args_parser.add_argument("-x64", action="store_true", default=False, dest="is64", 
        help="Run fasm.x64")
    args_parser.add_argument("--dump", action="store_true", default=False, dest="dump", 
        help="Dump opeartions without compilation")
    args_parser.add_argument("-stdo", "--stdout", dest="stdout", default=None, 
        help="File to output stdout of complier and program")
    args_parser.add_argument("-i", "--input", dest="input", default=None, 
        help="Stdin for program")
    args_parser.add_argument("-e", "--error", dest="error", default=None, 
        help="Stderr for program")
    args = args_parser.parse_args(sys.argv[1:])

    dump = args.dump
    run = args.run
    is64 = args.is64

    file_name = os.path.splitext(args.program)[0]

    with open(args.program, "r") as f:
        program = f.read() 

    sys.stdout = open(args.stdout, "w") if args.stdout else sys.stdout
    sys.stderr = open(args.error, "w") if args.error else sys.stderr
    sys.stdin = open(args.input, "r") if args.input else sys.stdin

    State.filename = file_name
    State.dir = os.path.dirname(__file__)

    ops = parse_to_ops(program)

    if dump:
        for op in ops:
            print(f"{op.loc} {op.type.name} {op.operand if op.type.name != 'OPERATOR' else op.operand.name}")
        return 

    type_check(ops)

    out = file_name if args.out is None else args.out

    with open(f"{out}.asm", "w") as f:
        f.write(generate_fasm(ops))

    if is64:
        subprocess.run(["fasm.x64", f"{out}.asm"], stdin=sys.stdin, stderr=sys.stderr)
    else:
        subprocess.run(["fasm", f"{out}.asm"], stdin=sys.stdin, stderr=sys.stderr)

    if run:
        subprocess.run([f"./{out}"], stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr)

if __name__ == "__main__":
    main()