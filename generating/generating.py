from parsing.op import * 

def generate_fasm(ops: list[Op]):
    buf = ""
    buf += """
format ELF64 executable 3
segment readable executable
_start:
"""

    for i in ops:
        buf += generate_op(i)

    buf += """
mov rax, 60
mov rdi, 0
syscall
"""

    return buf

def generate_op(op: Op):
    if op.type == OpType.PUSH_INT:
        return f"push {op.operand}\n"
    elif op.type == OpType.OPERATOR:
        return generate_operator(op)
    else:
        assert False, f"Generation isnt implemented for op type: {op.type.name}"

def generate_operator(op: Op):
    assert op.type == OpType.OPERATOR, f"generate_operator cant generate {op.type.name}"

    if op.operand in (Operator.ADD, Operator.SUB):
        return \
f"""
pop rax
pop rbx
{op.operand.name.lower()} rax, rbx
push rax
"""