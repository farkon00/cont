from parsing.op import * 

assert len(Operator) == 5, "Unimplemented operator in generating.py"
assert len(OpType) == 2, "Unimplemented type in generating.py"

def generate_fasm(ops: list):
    buf = ""
    buf += """
format ELF64 executable 3
segment readable executable
entry _start
print:
    mov     r9, -3689348814741910323
    sub     rsp, 40
    mov     BYTE [rsp+31], 10
    lea     rcx, [rsp+30]
.L2:
    mov     rax, rdi
    lea     r8, [rsp+32]
    mul     r9
    mov     rax, rdi
    sub     r8, rcx
    shr     rdx, 3
    lea     rsi, [rdx+rdx*4]
    add     rsi, rsi
    sub     rax, rsi
    add     eax, 48
    mov     BYTE [rcx], al
    mov     rax, rdi
    mov     rdi, rdx
    mov     rdx, rcx
    sub     rcx, 1
    cmp     rax, 9
    ja      .L2
    lea     rax, [rsp+32]
    mov     edi, 1
    sub     rdx, rax
    xor     eax, eax
    lea     rsi, [rsp+32+rdx]
    mov     rdx, r8
    mov     rax, 1
    syscall
    add     rsp, 40
    ret
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
    assert len(OpType) == 2, "Unimplemented type in generate_op"
    if op.type == OpType.PUSH_INT:
        return f"push {op.operand}\n"
    elif op.type == OpType.OPERATOR:
        return generate_operator(op)
    else:
        assert False, f"Generation isnt implemented for op type: {op.type.name}"

def generate_operator(op: Op):
    assert len(Operator) == 5, "Unimplemented operator in generate_operator"
    assert op.type == OpType.OPERATOR, f"generate_operator cant generate {op.type.name}"

    if op.operand in (Operator.ADD, Operator.SUB):
        return \
f"""
pop rax
pop rbx
{op.operand.name.lower()} rax, rbx
push rax
"""
    elif op.operand == Operator.MUL:
        return \
f"""
pop rax
pop rbx
mul rbx
push rax
"""
    elif op.operand == Operator.DIV:
        return \
f"""
xor rdx, rdx
pop rbx
pop rax
div rbx
push rax
push rdx
"""
    elif op.operand == Operator.PRINT:
        return \
"""
pop rdi
call print
"""
    else:
        assert False, f"Generation isnt implemented for operator: {op.operand.name}"