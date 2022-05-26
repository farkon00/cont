import sys

from parsing.parsing import parse_to_ops
from generating.generating import generate_fasm

def main():
    # Argv handeling
    run = False
    program = None
    for i in sys.argv[1:]:
        if i.startswith("--"):
            if i == "--help":
                print("Usage: cont.py <file> [options]")
                exit(0)
            else:
                print(f"Unknown option: {i}")
                exit(1)
        elif i.startswith("-"):
            if i == "-r":
                run = True
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
        print("Sorry, running isnt supported for now")
        exit(1)

if __name__ == "__main__":
    main()