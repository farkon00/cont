import sys
import os

from state import State
from parsing.parsing import parse_to_ops
from generating.generating import generate_fasm
from type_checking.type_checking import type_check

def main():
    # Argv handeling
    run = False
    is64 = False
    program = None
    for i in sys.argv[1:]:
        if i.startswith("--"):
            if i == "--help":
                print("Usage: cont.py <file> [options]")
                print("Options:")
                print("    --help        Show this help message")
                print("    -r            Automaticaly run the program")
                print("    -r64          Automaticaly run the program and use fasm.x64")
                print("    -x64          Use fasm.x64 for compiling fasm")
                exit(0)
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

    ops = parse_to_ops(program)

    type_check(ops)

    with open(f"{file_name}.asm", "w") as f:
        f.write(generate_fasm(ops))

    if is64:
        os.system(f"fasm.x64 {file_name}.asm")
    else:
        os.system(f"fasm {file_name}.asm")

    if run:
        os.system(f"./{file_name}")

if __name__ == "__main__":
    main()