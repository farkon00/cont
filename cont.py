from parsing.op import *
from generating.generating import generate_fasm

def main():
    ops = [
        Op(OpType.PUSH_INT, 1),
        Op(OpType.PUSH_INT, 2),
        Op(OpType.OPERATOR, Operator.ADD),
        Op(OpType.PUSH_INT, 1),
        Op(OpType.PUSH_INT, 2),
        Op(OpType.OPERATOR, Operator.SUB),
    ]

    with open("output.asm", "w") as f:
        f.write(generate_fasm(ops))

if __name__ == "__main__":
    main()