from parsing.op import * 
from type_checking.types import Array, sizeof
from state import *

assert len(Operator) == 20, "Unimplemented operator in generating.py"
assert len(OpType) == 40, "Unimplemented type in generating.py"

SYSCALL_ARGS = ["rax", "rdi", "rsi", "rdx", "r10", "r8", "r9"]

def generate_fasm(ops: list):
    buf = ""
    buf += """
format ELF64 executable 3
segment readable executable
entry _start
check_array_bounds:
    ;; rax - index
    ;; rbx - size of an array
    ;; r15 - loc pointer
    ;; r12 - loc size

    ;; if rax >= rbx
    cmp rax, rbx
    jl array_bound_if

    ;; write out of range text to stdout
    mov rax, 1
    mov rdi, 1
    mov rsi, index_out_of_range_text
    mov rdx, 22
    syscall

    ;; write loc to stdout
    mov rax, 1
    mov rdi, 1
    mov rsi, r15
    mov rdx, r12
    syscall

    ;; exit
    mov rax, 60
    mov rdi, 1
    syscall

    array_bound_if:
    ret

check_null_ptr:
    ;; rax - ptr
    ;; r15 - loc pointer
    ;; r12 - loc size

    ;; if ptr is null
    cmp rax, 0
    jne null_ptr_if

    ;; write null pointer dereference text to stdout
    mov rax, 1
    mov rdi, 1
    mov rsi, null_ptr_deref_text
    mov rdx, 28
    syscall

    ;; write loc to stdout
    mov rax, 1
    mov rdi, 1
    mov rsi, r15
    mov rdx, r12
    syscall

    ;; exit
    mov rax, 60
    mov rdi, 1
    syscall

    null_ptr_if:
    ret
_start:
"""

    for i in ops:
        if State.current_proc is not None and State.config.o_UPR:
            if State.current_proc not in State.used_procs:
                if i.type == OpType.ENDPROC:
                    State.current_proc = None
                continue
        buf += generate_op(i)

    buf += f"""
mov rax, 60
mov rdi, 0
syscall
segment readable writeable
mem: rb {Memory.global_offset}
call_stack_ptr: rb 8
bind_stack_ptr: rb 8
bind_stack: rb {State.config.size_bind_stack}
call_stack: rb {State.config.size_call_stack}
index_out_of_range_text: db "Index out of range in "
null_ptr_deref_text: db "Null pointer dereference in "
"""
    for index, i in enumerate(State.locs_to_include):
        buf += f"loc_{index}: db {', '.join([str(j) for j in bytes(i, encoding='utf-8')])}, 10\n"
    for index, i in enumerate(State.string_data):
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
    assert len(OpType) == 40, "Unimplemented type in generate_op"
    
    if not op.compiled:
        return ""

    State.loc = op.loc
    comment = generate_op_comment(op)

    if op.type == OpType.PUSH_INT:
        return comment + f"\nmov rax, {op.operand}\npush rax\n"
    elif op.type == OpType.PUSH_MEMORY:
        return comment + f"push mem+{op.operand}\n"
    elif op.type == OpType.PUSH_VAR:
        return comment + f"mov rax, [mem+{State.memories[op.operand].offset}]\npush rax\n"
    elif op.type == OpType.PUSH_VAR_PTR:
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
mov rax, [rbx]
push rax
"""
    elif op.type == OpType.PUSH_LOCAL_VAR_PTR:
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
        if op.operand not in State.used_procs and State.config.o_UPR:
            return ""
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
        assert State.current_proc is not None, "Bug in parsing of procedures"
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
        code = \
f"""
pop r11
pop rbx
mov r10, rbx
mov rax, {op.operand[0]}
mul rbx
add r11, rax
mov rbx, {'[r11]' if op.type == OpType.INDEX else 'r11'}
push rbx
"""
        if State.config.re_IOR: # Checking index out of range
                code += \
            f"""
            mov rax, r10
            mov rbx, {op.operand[1]}
            mov r15, loc_{op.loc_id}
            mov r12, {len(State.locs_to_include[op.loc_id]) + 1}
            call check_array_bounds
            """
        return comment + code
    elif op.type == OpType.ASM:
        return op.operand + "\n"
    elif op.type == OpType.CAST:
        return "" # Casts are type checking thing
    else:
        assert False, f"Generation isnt implemented for op type: {op.type.name}"

def generate_operator(op: Op):
    assert len(Operator) == 20, "Unimplemented operator in generate_operator"
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
    elif op.operand == Operator.OVER:
        return "pop rbx\npop rax\npush rax\npush rbx\npush rax\n"
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
f"""
pop rax
pop rbx
{f'''
mov r15, loc_{op.loc_id}
mov r12, {len(State.locs_to_include[op.loc_id]) + 1}
call check_null_ptr
''' if State.config.re_NPD else ''}

mov [rax], rbx
"""
    elif op.operand == Operator.LOAD:
        return \
f"""
pop rax
{f'''
mov r15, loc_{op.loc_id}
mov r12, {len(State.locs_to_include[op.loc_id]) + 1}
call check_null_ptr
''' if State.config.re_NPD else ''}

mov rbx, [rax]
push rbx 
"""
    elif op.operand == Operator.STORE8:
        return \
f"""
pop rax
pop rbx
{f'''
mov r15, loc_{op.loc_id}
mov r12, {len(State.locs_to_include[op.loc_id]) + 1}
call check_null_ptr
''' if State.config.re_NPD else ''}
mov [rax], bl
"""
    elif op.operand == Operator.LOAD8:
        return \
f"""
pop rax
{f'''
mov r15, loc_{op.loc_id}
mov r12, {len(State.locs_to_include[op.loc_id]) + 1}
call check_null_ptr
''' if State.config.re_NPD else ''}

xor rbx, rbx
mov bl, [rax]
push rbx
"""
    else:
        assert False, f"Generation isnt implemented for operator: {op.operand.name}"