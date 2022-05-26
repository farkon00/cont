import sys
import os

from parsing.parsing import parse_to_ops
from generating.generating import generate_fasm

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
                print("    -r            Automaticaly compile fasm and run the program")
                print("    -r64          Automaticaly compile fasm with fasm.x64 and run the program")
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
            else:
                print(f"Unknown option: {i}")
                exit(1)
        else:
            if program is not None:
                print(f"More than one file names were provided")
                exit(1)
            with open(i, "r") as f:
                program = f.read()
    if program is None:
        print("No program name was provided")
        exit(1)

    ops = parse_to_ops(program)

    with open("output.asm", "w") as f:
        f.write(generate_fasm(ops))

    if run:
        if is64:
            os.system("fasm.x64 output.asm")
        else:
            os.system("fasm output.asm")
        os.system("./output")

if __name__ == "__main__":
    main()