import subprocess
import sys
import os

from state import State
from parsing.parsing import parse_to_ops
from generating.generating import generate_fasm
from type_checking.type_checking import type_check

def main():
    # Argv handeling
    dump = False
    run = False
    is64 = False
    program = None

    args = (i for i in sys.argv[1:])

    for i in args:
        if i.startswith("--"):
            if i == "--help":
                print("Usage: cont.py <file> [options]")
                print("Options:")
                print("    --help        Show this help message")
                print("    -r            Automaticaly run the program")
                print("    -r64          Automaticaly run the program and use fasm.x64")
                print("    -x64          Use fasm.x64 for compiling fasm")
                print("    -o <path>     Moves stdout of program to <path>")
                print("    -i <path>     Moves stdin of program to <path>")
                print("    -e <path>     Moves stderr of program to <path>")
                exit(0)
            elif i == "--dump":
                dump = True
            else:
                print(f"Unknown option: {i}")
                exit(1)
        elif i.startswith("-"):
            if i == "-r":
                run = True
            elif i == "-r64":
                run = True
                is64 = True
            elif i == "-x64":
                is64 = True
            elif i == "-o":
                try:
                    sys.stdout = open(next(args), "w")
                except StopIteration:
                    print("Error: No file specified for -o")
                    exit(1)
            elif i == "-i":
                try:
                    sys.stdin = open(next(args), "r")
                except StopIteration:
                    print("Error: No file specified for -i")
                    exit(1)
            elif i == "-e":
                try:
                    sys.stderr = open(next(args), "w")
                except StopIteration:
                    print("Error: No file specified for -e")
                    exit(1)
            else:
                print(f"Unknown option: {i}")
                exit(1)
        else:
            if program is not None:
                print(f"More than one file names were provided")
                exit(1)
            with open(i, "r") as f:
                file_name = os.path.splitext(i)[0]
                program = f.read()
    if program is None:
        print("No program name was provided")
        exit(1)

    State.filename = file_name
    State.dir = os.path.dirname(__file__)

    ops = parse_to_ops(program)

    if dump:
        for op in ops:
            print(f"{op.loc} {op.type.name} {op.operand if op.type.name != 'OPERATOR' else op.operand.name}")
        return 

    type_check(ops)

    with open(f"{file_name}.asm", "w") as f:
        f.write(generate_fasm(ops))

    if is64:
        subprocess.run(["fasm.x64", f"{file_name}.asm"], stdin=sys.stdin, stderr=sys.stderr)
    else:
        subprocess.run(["fasm", f"{file_name}.asm"], stdin=sys.stdin, stderr=sys.stderr)

    if run:
        subprocess.run([f"./{file_name}"], stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr)

if __name__ == "__main__":
    main()