from parsing.op import * 
from type_checking.types import Array, sizeof
from state import *

assert len(Operator) == 19, "Unimplemented operator in generating.py"
assert len(OpType) == 35, "Unimplemented type in generating.py"

SYSCALL_ARGS = ["rax", "rdi", "rsi", "rdx", "r10", "r8", "r9"]

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

    buf += f"""
mov rax, 60
mov rdi, 0
syscall
segment readable writeable
mem: rb {Memory.global_offset}
call_stack_ptr: rb 8
bind_stack_ptr: rb 8
bind_stack: rb 8192
call_stack: rb 65536
"""
    for index, i in enumerate(State.string_data):
        # Second expression is converting string to its bytes representation
        buf += f"str_{index}: db {', '.join([str(j) for j in i])}\n"

    return buf

def generate_op_comment(op : Op):
    buf = f";; {State.loc} {op.type.name} "
    if op.type == OpType.OPERATOR:
        buf += f"{op.operand.name}\n"
    elif isinstance(op.operand, Block):
        buf += f"Block: {op.operand.type.name} {op.operand.start} - {op.operand.end}\n"
    else:
        buf += f"{op.operand}\n"
    return buf

def generate_op(op: Op):
    assert len(OpType) == 35, "Unimplemented type in generate_op"
    
    State.loc = op.loc
    comment = generate_op_comment(op)

    if op.type == OpType.PUSH_INT:
        return comment + f"\nmov rax, {op.operand}\npush rax\n"
    elif op.type == OpType.PUSH_MEMORY:
        return comment + f"push mem+{op.operand}\n"
    elif op.type == OpType.PUSH_VAR:
        return comment + f"push mem+{State.memories[op.operand].offset}\n"
    elif op.type == OpType.PUSH_LOCAL_MEM:
        assert State.current_proc is not None, "Bug in parsing of local and global memories"
        return comment + \
f"""
mov rbx, [call_stack_ptr]
add rbx, call_stack
sub rbx, {State.current_proc.memory_size + op.operand + 8}\n
push rbx
"""
    elif op.type == OpType.PUSH_LOCAL_VAR:
        assert State.current_proc is not None, "Bug in parsing of local and global memories"
        return comment + \
f"""
mov rbx, [call_stack_ptr]
add rbx, call_stack
sub rbx, {State.current_proc.memory_size + State.current_proc.memories[op.operand].offset + 8}
push rbx
"""
    elif op.type == OpType.PUSH_STR:
        return comment + f"push {len(State.string_data[op.operand])}\npush str_{op.operand}\n"
    elif op.type == OpType.PUSH_NULL_STR:
        return comment + f"push str_{op.operand}\n"
    elif op.type == OpType.PUSH_PROC:
        return comment + f"push addr_{op.operand}\n"
    elif op.type == OpType.OPERATOR:
        return comment + generate_operator(op)
    elif op.type == OpType.SYSCALL:
        buf = ""
        for i in range(op.operand + 1):
            buf += f"pop {SYSCALL_ARGS[i]}\n"
        buf += f"syscall\npush rax\n\n"
        return comment + buf
    elif op.type == OpType.IF:
        return comment + \
f"""
pop rax
cmp rax, 0
jz addr_{op.operand.end}
"""
    elif op.type == OpType.ELSE:
        return comment + \
f"""
jmp addr_{op.operand.end}
addr_{op.operand.start}:
"""
    elif op.type == OpType.ENDIF:
        return comment + \
f"""
addr_{op.operand.end}:
"""
    elif op.type == OpType.WHILE:
        return comment + \
f"""
addr_{op.operand.start}:
pop rax
cmp rax, 0
jz addr_{op.operand.end}
"""
    elif op.type == OpType.ENDWHILE:
        return comment + \
f"""
jmp addr_{op.operand.start}
addr_{op.operand.end}:
"""
    elif op.type == OpType.DEFPROC:
        State.current_proc = op.operand
        return comment + \
f"""
jmp addr_{op.operand.block.end}
addr_{op.operand.ip}:
pop rax
mov rbx, [call_stack_ptr]
add rbx, {op.operand.memory_size}
mov [call_stack+rbx], rax
add rbx, 8
mov [call_stack_ptr], rbx
"""
    elif op.type == OpType.ENDPROC:
        assert State.current_proc is not None, "Bug in parsing of local and global memories"
        asm = comment + \
f"""
mov rbx, [call_stack_ptr]
sub rbx, 8
mov [call_stack_ptr], rbx

mov rax, [call_stack+rbx]
push rax
sub rbx, {State.current_proc.memory_size}
mov [call_stack_ptr], rbx
ret
addr_{op.operand.end}:
"""

        State.current_proc = None
        return asm
    elif op.type == OpType.BIND:
        buf = comment
        State.bind_stack_size += op.operand
        for i in range(op.operand):
            buf += \
f"""
pop rax
mov rbx, [bind_stack_ptr]
add rbx, {(op.operand - i - 1) * 8}
mov [bind_stack+rbx], rax
"""    
        buf += \
f"""
mov rax, [bind_stack_ptr]
add rax, {op.operand * 8}
mov [bind_stack_ptr], rax
"""
        return buf
    elif op.type == OpType.UNBIND:
        State.bind_stack_size -= op.operand
        return comment + \
f"""
mov rbx, [bind_stack_ptr]
sub rbx, {op.operand * 8}
mov [bind_stack_ptr], rbx
"""  
    elif op.type == OpType.PUSH_BIND_STACK:
        return comment + \
f"""
mov rbx, bind_stack-{(State.bind_stack_size - op.operand)*8}
mov rcx, [bind_stack_ptr]
mov rax, [rbx+rcx]
push rax
"""
    elif op.type == OpType.CALL:
        return comment + f"call addr_{op.operand.ip}\n"
    elif op.type == OpType.TYPED_LOAD:
        assert not isinstance(op.operand, Struct), "Bug in parsing of structure types"
        return comment + \
"""
pop rax
mov rbx, [rax]
push rbx 
"""
    elif op.type == OpType.TYPED_STORE:
        assert not isinstance(op.operand, Struct), "Bug in parsing of structure types"
        return comment + \
"""
pop rax
pop rbx
mov [rax], rbx
"""
    elif op.type == OpType.PACK:
        struct = State.structures[op.operand]
        size = sizeof(struct)
        buf = comment + \
f"""
mov rdi, 0
mov rax, 12
syscall
mov rbx, rax
add rax, {size}
mov rdi, rax
mov rax, 12
syscall
mov rcx, [bind_stack_ptr]
mov [bind_stack+rcx], rbx
add rcx, 8
mov [bind_stack_ptr], rcx
"""
        if "__init__" in struct.methods:
            buf += \
f"""
push rbx
call addr_{struct.methods['__init__'].ip}
"""
        else:
            offset = 0
            for index, field in list(enumerate(struct.fields_types))[::-1]:
                offset += sizeof(field)
                if index not in struct.defaults:
                    buf += f"\npop rax\n"         
                else:
                    buf += f"\nmov rax, {struct.defaults[index]}\n"

                buf += f"\nmov [rbx+{size-offset}], rax\n"

        buf += \
f"""
mov rcx, [bind_stack_ptr]
sub rcx, 8
mov rax, [bind_stack+rcx] 
mov [bind_stack_ptr], rcx
push rax
"""

        return buf
    elif op.type == OpType.UNPACK:
        buf = comment + "\npop rax\n"
        for i in range(op.operand // 8):
            buf += \
f"""
mov rbx, [{i*8}+rax]
push rbx
"""
        return buf
    elif op.type == OpType.MOVE_STRUCT:
        buf = comment + "\npop rbx\npop rax\n"
        for i in range(op.operand // 8):
            buf += \
f"""
mov rcx, [rax+{i*8}]
mov [rbx+{i*8}], rcx
"""

        return buf
    elif op.type == OpType.PUSH_FIELD:
        return comment + \
f"""
pop rax
mov rbx, [rax+{op.operand}]
push rbx
"""
    elif op.type == OpType.PUSH_FIELD_PTR:
        return comment + \
f"""
pop rax
add rax, {op.operand}
push rax
"""
    elif op.type == OpType.UPCAST:
        buf = comment + \
f"""
pop rbx
mov rdi, 0
mov rax, 12
syscall
mov rdx, rax
add rax, {op.operand[0]}
mov rdi, rax
mov rax, 12
syscall
"""
        for i in range(op.operand[2] // 8):
            buf += \
f"""
mov rcx, [rbx+{i*8}]
mov [rdx+{i*8}], rcx
"""

        for i in range(op.operand[1]):
            buf += \
f"""
pop rcx
mov [rdx+{op.operand[0]-(i+1)*8}], rcx
"""
        buf += "\npush rdx\n"
        return buf
    elif op.type == OpType.AUTO_INIT: 
        if State.current_proc is not None:
            memory = \
f"""
mov r12, [call_stack_ptr]
add r12, call_stack
sub r12, {State.current_proc.memory_size + op.operand[0].offset + 8}
"""
        else:
            memory = f"\nmov r12, mem+{op.operand[0].offset}\n"
        if State.current_proc is None:
            var: Array = State.variables[op.operand[0].name] # type: ignore
        else:
            var = State.current_proc.variables[op.operand[0].name] # type: ignore
        return comment + \
f"""
;; loop
mov rdi, 0
addr_{op.operand[1]}_1:
cmp rdi, {var.len}
je addr_{op.operand[1]}_2

{memory}

;; get ptr to array element into r10
mov r10, r12
mov rax, 8
mul rdi
add r10, rax

;; put ptr to struct into r11
add r12, {sizeof(var)}
mov r11, r12
mov rax, {sizeof(var.typ.typ)}
mul rdi
add r11, rax

;; moves ptr into array
mov [r10], r11 

add rdi, 1

jmp addr_{op.operand[1]}_1
addr_{op.operand[1]}_2:
"""
    elif op.type == OpType.CALL_LIKE:
        return comment + \
f"""
pop rax
call rax
"""
    elif op.type in (OpType.INDEX, OpType.INDEX_PTR):
        return comment + \
f"""
pop r10
pop rbx
mov rax, {op.operand}
mul rbx
add r10, rax
mov rbx, {'[r10]' if op.type == OpType.INDEX else 'r10'}
push rbx
"""
    elif op.type == OpType.CAST:
        return "" # Casts are type checking thing
    else:
        assert False, f"Generation isnt implemented for op type: {op.type.name}"

def generate_operator(op: Op):
    assert len(Operator) == 19, "Unimplemented operator in generate_operator"
    assert op.type == OpType.OPERATOR, f"generate_operator cant generate {op.type.name}"

    if op.operand in (Operator.ADD, Operator.SUB):
        return \
f"""
pop rbx
pop rax
{op.operand.name.lower()} rax, rbx
push rax
"""
    elif op.operand == Operator.MUL:
        return \
f"""
pop rbx
pop rax
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
    elif op.operand == Operator.DUP:
        return "pop rax\npush rax\npush rax\n"
    elif op.operand == Operator.DROP:
        return "pop rax\n"
    elif op.operand == Operator.SWAP:
        return "pop rbx\npop rax\npush rbx\npush rax\n"
    elif op.operand == Operator.ROT:
        return "pop rcx\npop rbx\npop rax\npush rcx\npush rbx\npush rax\n"
    elif op.operand in (Operator.LT, Operator.GT, Operator.EQ):
        return \
f"""
mov rcx, 0
mov rdx, 1
pop rbx
pop rax
cmp rax, rbx
cmov{op.operand.name.lower()[0]} rcx, rdx
push rcx
"""
    elif op.operand in (Operator.LE, Operator.GE, Operator.NE):
        return \
f"""
mov rcx, 0
mov rdx, 1
pop rbx
pop rax
cmp rax, rbx
cmov{op.operand.name.lower()} rcx, rdx
push rcx
"""
    elif op.operand == Operator.STORE:
        return \
"""
pop rax
pop rbx
mov [rax], rbx
"""
    elif op.operand == Operator.LOAD:
        return \
"""
pop rax
mov rbx, [rax]
push rbx 
"""
    elif op.operand == Operator.STORE8:
        return \
"""
pop rax
pop rbx
mov [rax], bl
"""
    elif op.operand == Operator.LOAD8:
        return \
"""
pop rax
xor rbx, rbx
mov bl, [rax]
push rbx
"""
    else:
        assert False, f"Generation isnt implemented for operator: {op.operand.name}"