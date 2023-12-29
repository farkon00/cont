import subprocess
import os
import stat

from typing import List, Set

from parsing.op import *
from type_checking.types import Array, sizeof
from state import *
from type_checking.types import *

assert len(Operator) == 20, "Unimplemented operator in fasm_x86_64_linux.py"
assert len(OpType) == 40, "Unimplemented type in fasm_x86_64_linux.py"

SYSCALL_ARGS = ["rax", "rdi", "rsi", "rdx", "r10", "r8", "r9"]


def compile_ops_fasm_x86_64_linux(ops: List[Op]):
    """
    The main entry point to the generation step of the compilation process
    for the fasm_x86_64_linux target. Handles the generation of assembly,
    assembling the executable and running it if needed.

    `ops` is a list of operations to be compiled, which includes all the ops from the
    included files and the ops from the main file, that is being compiled. The operations
    should be processed by the type checker before being given to this function.
    """
    if subprocess.getstatusoutput("fasm")[0] == 127:
        print("Please install Flat Assembler (Fasm).")
        print("Use sudo apt install fasm if you are using Debian/Ubuntu")
        exit(1)

    out = State.filename if State.config.out is None else State.config.out

    with open(f"{out}.asm", "w") as f:
        f.write(generate_fasm_x86_64_linux(ops))

    subprocess.run(["fasm", f"{out}.asm"], stdin=sys.stdin, stderr=sys.stderr)
    os.chmod(
        out, os.stat(out).st_mode | stat.S_IEXEC
    )  # Give execution permission to the file

    if State.config.run:
        subprocess.run(
            [f"./{out}"], stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr
        )

INDEX_ERROR_CODE = (
    "check_array_bounds:\n"
    ";; rax - index\n"
    ";; rbx - size of an array\n"
    ";; r15 - loc pointer\n"
    ";; r12 - loc size\n"

    ";; if rax >= rbx\n"
    "cmp rax, rbx\n"
    "jl array_bound_if\n"

    ";; write out of range text to stdout\n"
    "mov rax, 1\n"
    "mov rdi, 1\n"
    "mov rsi, index_out_of_range_text\n"
    "mov rdx, 22\n"
    "syscall\n"
    
    ";; write loc to stdout\n"
    "mov rax, 1\n"
    "mov rdi, 1\n"
    "mov rsi, r15\n"
    "mov rdx, r12\n"
    "syscall\n"
    
    ";; exit\n"
    "mov rax, 60\n"
    "mov rdi, 1\n"
    "syscall\n"
    "array_bound_if:\n"
    "ret\n"
)
NULL_POINTER_CODE = (
    "check_null_ptr:\n"
    ";; rax - ptr\n"
    ";; r15 - loc pointer\n"
    ";; r12 - loc size\n"

    ";; if ptr is null\n"
    "cmp rax, 0\n"
    "jne null_ptr_if\n"

    ";; write null pointer dereference text to stdout\n"
    "mov rax, 1\n"
    "mov rdi, 1\n"
    "mov rsi, null_ptr_deref_text\n"
    "mov rdx, 28\n"
    "syscall\n"

    ";; write loc to stdout\n"
    "mov rax, 1\n"
    "mov rdi, 1\n"
    "mov rsi, r15\n"
    "mov rdx, r12\n"
    "syscall\n"

    ";; exit\n"
    "mov rax, 60\n"
    "mov rdi, 1\n"
    "syscall\n"

    "null_ptr_if:\n"
    "ret\n"
)

def generate_fasm_x86_64_linux(ops: List[Op]) -> str:
    """Generates a string of fasm assembly for the program from the list of operations `ops`."""
    buf = (
        "format ELF64 executable 3\n"
        "segment readable executable\n"
        "entry _start\n"
        f"{INDEX_ERROR_CODE if State.config.re_IOR else ''}"
        f"{NULL_POINTER_CODE if State.config.re_NPD else ''}"
        "_start:\n"
    )

    for op in ops:
        if State.current_proc is not None and State.config.o_UPR:
            if State.current_proc not in State.used_procs:
                if op.type == OpType.PROC_RETURN and op.operand[1]:
                    State.current_proc = None
                continue
        buf += generate_op_fasm_x86_64_linux(op)

    ior_code = 'index_out_of_range_text: db "Index out of range in "'
    npd_code = 'null_ptr_deref_text: db "Null pointer dereference in "'
    buf += (
        "mov rax, 60\n"
        "xor rdi, rdi\n"
        "syscall\n"
        "segment readable writeable\n"
        f"{ior_code if State.config.re_IOR else ''}\n"
        f"{npd_code if State.config.re_NPD else ''}\n"
        f"{generate_fasm_types()}\n"
    )

    for index, loc in enumerate(State.locs_to_include):
        buf += f"loc_{index}: db {', '.join([str(j) for j in bytes(loc, encoding='utf-8')])}, 10\n"
    for index, string in enumerate(State.string_data):
        if len(string) != 0:
            buf += f"str_{index}: db {', '.join([str(j) for j in string])}\n"
        else:
            buf += f"str_{index}:\n"

    buf += (
        f"{f'mem: rb {Memory.global_offset}' if Memory.global_offset else ''}\n"
        "call_stack_ptr: rb 8\n"
        "bind_stack_ptr: rb 8\n"
        f"bind_stack: rb {State.config.size_bind_stack}\n"
        f"call_stack: rb {State.config.size_call_stack}\n"
    )

    return buf


def generate_fasm_types() -> str:
    """
    Generates a string of assembly, which if put into the .data segment,
    will define all the runtimed types in the static memmory.
    """
    buf = ""
    queue_set = State.runtimed_types_set.copy()
    queue_list = State.runtimed_types_list.copy()
    generated_types: Set[object] = set()
    while queue_list:
        typ = queue_list.pop()
        queue_set.remove(typ)
        if typ.text_repr() in generated_types:
            continue
        generated_types.add(typ.text_repr())
        buf += generate_fasm_type(typ, queue_set, queue_list, generated_types) + "\n"
    return buf


def generate_fasm_type(typ: Type, queue_set: Set[Type], queue_list: List[Type], generated_types: Set[str]):
    """
    Generates a fasm assembly string with the dq derictive,
    which stores the bytes for the Type struct in static memory.
    
    * `typ` is the type to be runtimed.
    * `queue_set` is a queue, that includes all the types to be generated
    * `queue_list` is a queue, that includes all the types to be generated
    * `generated_types` is a set of all types, that have already been generated
    
    The last three parameters should stay the same objects between
    different calls of this function in the same compilations.
    """
    addr = f"type_{typ.text_repr()}: "
    if isinstance(typ, Int):
        return addr + f"dq {State.TYPE_IDS['int']},8,1"
    elif isinstance(typ, Addr):
        buf = addr + f"dq {State.TYPE_IDS['addr']},8,1,$+16,$+{8 + (len(typ.in_types) + 1) * 8}"
        for field in typ.in_types:
            if typ not in generated_types:
                if field not in queue_set:
                    queue_set.add(field)
                    queue_list.append(field)
            buf += f",type_{field.text_repr()}"
        buf += ",0"
        for field in typ.out_types:
            if typ not in generated_types:
                if field not in queue_set:
                    queue_set.add(field)
                    queue_list.append(field)
            buf += f",type_{field.text_repr()}"
        return buf + ",0"
    elif isinstance(typ, Ptr):
        if typ.typ is None:
            return addr + f"dq {State.TYPE_IDS['ptr']},8,1,0"
        else:
            if typ not in generated_types:
                if typ.typ not in queue_set:
                    queue_set.add(typ.typ)
                    queue_list.append(typ.typ)
            return addr + f"dq {State.TYPE_IDS['ptr']},8,1,type_{typ.typ.text_repr()}"
    elif isinstance(typ, Array):
        cont_assert(typ.len != -1 and typ.typ is not None, 
            "In lang(impossible to create by user) array given to generate_fasm_type")
        if typ not in generated_types:
            if typ.typ not in queue_set:
                queue_set.add(typ.typ)
                queue_list.append(typ.typ)
        return (
            addr
            + f"dq {State.TYPE_IDS['array']},8,1,type_{typ.typ.text_repr()},{typ.len}"
        )
    elif isinstance(typ, Struct):
        State.curr_type_id += 1
        buf = addr + f"dq {State.curr_type_id},{sizeof(typ)},0,"
        if typ.parent is not None:
            buf += f"type_{typ.parent.text_repr()}"
        else:
            buf += "0"
        buf += ",$+8"
        for field in typ.fields_types:
            if typ not in generated_types:
                if field not in queue_set:
                    queue_set.add(field)
                    queue_list.append(field)
            buf += f",type_{field.text_repr()}"
        return buf + ",0"  # Null for the end of fields


def generate_op_comment(op: Op):
    """Generates a comment, describing the operation `op`."""
    buf = f";; {State.loc} {op.type.name} "
    if op.type == OpType.OPERATOR:
        buf += f"{op.operand.name}\n"
    elif isinstance(op.operand, Block):
        buf += f"Block: {op.operand.type.name} {op.operand.start} - {op.operand.end}\n"
    else:
        buf += f"{op.operand}\n"
    return buf


def generate_op_fasm_x86_64_linux(op: Op) -> str:
    """
    Generates and returns the string of assembly to be
    put into the executable segment for the operation `op`.
    """
    cont_assert(len(OpType) == 40, "Unimplemented type in generate_op")

    if not op.compiled:
        return ""

    State.loc = op.loc
    comment = generate_op_comment(op)

    if op.type == OpType.PUSH_INT:
        if op.operand == 0:
            mov = f"xor rax, rax"
        else:
            mov = f"mov rax, {op.operand}"
        return comment + f"\n{mov}\npush rax\n"
    elif op.type == OpType.PUSH_MEMORY:
        return comment + f"push mem+{op.operand}\n"
    elif op.type == OpType.PUSH_VAR:
        return (
            comment + f"mov rax, [mem+{State.memories[op.operand].offset}]\npush rax\n"
        )
    elif op.type == OpType.PUSH_VAR_PTR:
        return comment + f"push mem+{State.memories[op.operand].offset}\n"
    elif op.type == OpType.PUSH_LOCAL_MEM:
        cont_assert(State.current_proc is not None, 
            "Bug in parsing of local and global memories")
        return comment + (
            "mov rbx, [call_stack_ptr]\n"
            "add rbx, call_stack\n"
            f"sub rbx, {State.current_proc.memory_size + 8 - op.operand}\n"
            "push rbx\n"
        )
    elif op.type == OpType.PUSH_LOCAL_VAR:
        cont_assert(State.current_proc is not None, 
            "Bug in parsing of local and global memories")
        return comment + (
            "mov rbx, [call_stack_ptr]\n"
            "add rbx, call_stack\n"
            f"sub rbx, {State.current_proc.memory_size + 8 - State.current_proc.memories[op.operand].offset}\n"
            "mov rax, [rbx]\n"
            "push rax\n"
        )
    elif op.type == OpType.PUSH_LOCAL_VAR_PTR:
        cont_assert(State.current_proc is not None, 
            "Bug in parsing of local and global memories")
        return comment + (
            "mov rbx, [call_stack_ptr]\n"
            "add rbx, call_stack\n"
            f"sub rbx, {State.current_proc.memory_size + 8 - State.current_proc.memories[op.operand].offset}\n"
            "push rbx\n"
        )
    elif op.type == OpType.PUSH_STR:
        return (
            comment
            + f"push {len(State.string_data[op.operand])}\npush str_{op.operand}\n"
        )
    elif op.type == OpType.PUSH_NULL_STR:
        return comment + f"push str_{op.operand}\n"
    elif op.type == OpType.PUSH_PROC:
        return comment + f"push addr_{op.operand.ip}\n"
    elif op.type == OpType.OPERATOR:
        return comment + generate_operator_fasm_x86_64_linux(op)
    elif op.type == OpType.SYSCALL:
        buf = ""
        for i in range(op.operand + 1):
            buf += f"pop {SYSCALL_ARGS[i]}\n"
        buf += f"syscall\npush rax\n\n"
        return comment + buf
    elif op.type == OpType.IF:
        return comment + (
            "pop rax\n"
            "cmp rax, 0\n"
            f"jz addr_{op.operand.end}\n"
        )
    elif op.type == OpType.ELSE:
        return comment + (
            f"jmp addr_{op.operand.end}\n"
            f"addr_{op.operand.start}:\n"
        )
    elif op.type == OpType.ENDIF:
        return comment + f"addr_{op.operand.end}:\n"
    elif op.type == OpType.WHILE:
        return comment + (
            f"addr_{op.operand.start}:\n"
            "pop rax\n"
            "cmp rax, 0\n"
            f"jz addr_{op.operand.end}\n"
        )
    elif op.type == OpType.ENDWHILE:
        return comment + (
            f"jmp addr_{op.operand.start}\n"
            f"addr_{op.operand.end}:\n"
        )
    elif op.type == OpType.DEFPROC:
        State.current_proc = op.operand
        if op.operand not in State.used_procs and State.config.o_UPR:
            return ""
        return comment + (
            f"jmp addr_{op.operand.block.end}\n"
            f"addr_{op.operand.ip}:\n"
            "pop rax\n"
            "mov rbx, [call_stack_ptr]\n"
            f"add rbx, {op.operand.memory_size}\n"
            "mov [call_stack+rbx], rax\n"
            "add rbx, 8\n"
            "mov [call_stack_ptr], rbx\n"
        )
    elif op.type == OpType.PROC_RETURN:
        cont_assert(State.current_proc is not None, "Bug in parsing of procedures")
        asm = comment + (
            "mov rbx, [call_stack_ptr]\n"
            "sub rbx, 8\n"
            "mov [call_stack_ptr], rbx\n"
            "mov rax, [call_stack+rbx]\n"
            "push rax\n"
            f"sub rbx, {State.current_proc.memory_size}\n"
            "mov [call_stack_ptr], rbx\n"
            "ret\n"
        )

        if op.operand[1]:
            asm += f"addr_{op.operand[0].end}:\n"
            State.current_proc = None
        return asm
    elif op.type == OpType.BIND:
        buf = comment
        State.bind_stack_size += op.operand
        for i in range(op.operand):
            buf += (
                "pop rax\n"
                "mov rbx, [bind_stack_ptr]\n"
                f"add rbx, {(op.operand - i - 1) * 8}\n"
                "mov [bind_stack+rbx], rax\n"
            )
        buf += (
            "mov rax, [bind_stack_ptr]\n"
            f"add rax, {op.operand * 8}\n"
            "mov [bind_stack_ptr], rax\n"
        )

        return buf
    elif op.type == OpType.UNBIND:
        if op.operand[1]: State.bind_stack_size -= op.operand[0]
        return comment + (
            "mov rbx, [bind_stack_ptr]\n"
            f"sub rbx, {op.operand[0] * 8}\n"
            "mov [bind_stack_ptr], rbx\n"
        )
    elif op.type == OpType.PUSH_BIND_STACK:
        return comment + (
            f"mov rbx, bind_stack-{(State.bind_stack_size - op.operand)*8}\n"
            "mov rcx, [bind_stack_ptr]\n"
            "mov rax, [rbx+rcx]\n"
            "push rax\n"
        )
    elif op.type == OpType.CALL:
        return comment + f"call addr_{op.operand.ip}\n"
    elif op.type == OpType.TYPED_LOAD:
        cont_assert(not isinstance(op.operand, Struct), "Bug in parsing of structure types")
        return comment + (
            "pop rax\n"
            "mov rbx, [rax]\n"
            "push rbx\n"
        )
    elif op.type == OpType.PACK:
        struct = State.structures[op.operand[0]]
        size = sizeof(struct)
        if op.operand[1]:
            if State.config.struct_malloc[1]:
                assert not State.procs["malloc"].is_imported, "Cannot import malloc in fasm_x86_64_linux target"
                buf = comment + (
                    f"push {size}\n"
                    f"call addr_{State.procs['malloc'].ip}\n"
                    "pop rbx\n"
                )
            else:
                buf = comment + (
                    "xor rdi, rdi\n"
                    "mov rax, 12\n"
                    "syscall\n"
                    "mov rbx, rax\n"
                    f"add rax, {size}\n"
                    "mov rdi, rax\n"
                    "mov rax, 12\n"
                    "syscall\n"
                )
        else:
            buf = comment + "\npop rbx\n"

        buf += (
            "mov rcx, [bind_stack_ptr]\n"
            "mov [bind_stack+rcx], rbx\n"
            "add rcx, 8\n"
            "mov [bind_stack_ptr], rcx\n"
        )
        if "__init__" in struct.methods:
            buf += (
                "push rbx\n"
                f"call addr_{struct.methods['__init__'].ip}\n"
            )
        else:
            offset = 0
            for index, field in list(enumerate(struct.fields_types))[::-1]:
                offset += sizeof(field)
                if index not in struct.defaults:
                    buf += f"\npop rax\n"
                else:
                    buf += f"\nmov rax, {struct.defaults[index]}\n"

                buf += f"\nmov [rbx+{size-offset}], rax\n"

        buf += (
            "mov rcx, [bind_stack_ptr]\n"
            "sub rcx, 8\n"
            "mov rax, [bind_stack+rcx]\n"
            "mov [bind_stack_ptr], rcx\n"
            "push rax\n"
        )

        return buf
    elif op.type == OpType.UNPACK:
        buf = comment + "\npop rax\n"
        for i in range(op.operand // 8):
            buf += (
                f"mov rbx, [{i*8}+rax]\n"
                "push rbx\n"
            )
        return buf
    elif op.type == OpType.MOVE_STRUCT:
        buf = comment + "\npop rbx\npop rax\n"
        for i in range(op.operand // 8):
            buf += (
                f"mov rcx, [rax+{i*8}]\n"
                f"mov [rbx+{i*8}], rcx\n"
            )

        return buf
    elif op.type == OpType.PUSH_FIELD:
        return comment + (
            "pop rax\n"
            f"mov rbx, [rax+{op.operand}]\n"
            "push rbx\n"
        )
    elif op.type == OpType.PUSH_FIELD_PTR:
        return comment + (
            "pop rax\n"
            f"add rax, {op.operand}\n"
            "push rax\n"
        )
    elif op.type == OpType.UPCAST:
        if State.config.struct_malloc[1]:
            assert not State.procs["malloc"].is_imported, "Cannot import malloc in fasm_x86_64_linux target"
            buf = comment + (
                f"push {op.operand[0]}\n"
                f"call addr_{State.procs['malloc'].ip}\n"
                "pop rdx\n"
                "pop rbx\n"
            )
        else:
            buf = comment + (
                "pop rbx\n"
                "xor rdi, rdi\n"
                "mov rax, 12\n"
                "syscall\n"
                "mov rdx, rax\n"
                f"add rax, {op.operand[0]}\n"
                "mov rdi, rax\n"
                "mov rax, 12\n"
                "syscall\n"
            )
        for i in range(op.operand[2] // 8):
            buf += (
                f"mov rcx, [rbx+{i*8}]\n"
                f"mov [rdx+{i*8}], rcx\n"
            )

        for i in range(op.operand[1]):
            buf += (
                "pop rcx\n"
                f"mov [rdx+{op.operand[0]-(i+1)*8}], rcx\n"
            )

        buf += "\npush rdx\n"
        return buf
    elif op.type == OpType.AUTO_INIT:
        if State.current_proc is not None:
            memory = (
                "mov r12, [call_stack_ptr]\n"
                "add r12, call_stack\n"
                f"sub r12, {State.current_proc.memory_size + op.operand[0].offset + 8}\n"
            )
        else:
            memory = f"\nmov r12, mem+{op.operand[0].offset}\n"
        if State.current_proc is None:
            var: Array = State.variables[op.operand[0].name]  # type: ignore
        else:
            var: Array = State.current_proc.variables[op.operand[0].name]  # type: ignore
        return comment + (
            ";; loop\n"
            "xor rdi, rdi\n"
            f"addr_{op.operand[1]}_1:\n"
            f"cmp rdi, {var.len}\n"
            f"je addr_{op.operand[1]}_2\n"

            f"{memory}\n"

            ";; get ptr to array element into r10\n"
            "mov r10, r12\n"
            "mov rax, 8\n"
            "mul rdi\n"
            "add r10, rax\n"

            ";; put ptr to struct into r11\n"
            f"add r12, {sizeof(var)}\n"
            "mov r11, r12\n"
            f"mov rax, {sizeof(var.typ.typ)}\n"
            "mul rdi\n"
            "add r11, rax\n"

            ";; moves ptr into array\n"
            "mov [r10], r11 \n"

            "add rdi, 1\n"

            f"jmp addr_{op.operand[1]}_1\n"
            f"addr_{op.operand[1]}_2:\n"
        )
    elif op.type == OpType.CALL_ADDR:
        return comment + "pop rax\ncall rax\n"

    elif op.type in (OpType.INDEX, OpType.INDEX_PTR):
        code = (
            "pop r11\n"
            "pop rbx\n"
            "mov r10, rbx\n"
            f"mov rax, {op.operand[0]}\n"
            "mul rbx\n"
            "add r11, rax\n"
            f"mov rbx, {'[r11]' if op.type == OpType.INDEX else 'r11'}\n"
            "push rbx\n"
        )
        if State.config.re_IOR:  # Checking index out of range
            code += (
                "mov rax, r10\n"
                f"mov rbx, {op.operand[1]}\n"
                f"mov r15, loc_{op.loc_id}\n"
                f"mov r12, {len(State.locs_to_include[op.loc_id]) + 1}\n"
                "call check_array_bounds\n"
            )
        return comment + code
    elif op.type == OpType.ASM:
        return op.operand + "\n"
    elif op.type == OpType.PUSH_TYPE:
        return comment + f"push type_{op.operand.text_repr()}\n"
    elif op.type == OpType.CAST:
        return ""  # Casts are type checking thing
    else:
        cont_assert(False, f"Generation isn't implemented for op type: {op.type.name}")


def generate_operator_fasm_x86_64_linux(op: Op):
    """
    Generates and returns a string of assembly for an operation `op`,
    which must have the type `OpType.OPERATOR`.
    """
    cont_assert(len(Operator) == 20, "Unimplemented operator in generate_operator_fasm_x86_64_linux")
    cont_assert(op.type == OpType.OPERATOR, f"generate_operator_fasm_x86_64_linux cant generate {op.type.name}")

    call_npd_code = (
        f"mov r15, loc_{op.loc_id}\n"
        f"mov r12, {len(State.locs_to_include[op.loc_id]) + 1}\n"
        "call check_null_ptr\n"
    )

    if op.operand in (Operator.ADD, Operator.SUB):
        return (
            "pop rbx\n"
            "pop rax\n"
            f"{op.operand.name.lower()} rax, rbx\n"
            "push rax\n"
        )
    elif op.operand == Operator.MUL:
        return (
            "pop rbx\n"
            "pop rax\n"
            "mul rbx\n"
            "push rax\n"
        )
    elif op.operand == Operator.DIV:
        return (
            "xor rdx, rdx\n"
            "pop rbx\n"
            "pop rax\n"
            "idiv rbx\n"
            "push rax\n"
            "push rdx\n"
        )
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
        return (
            "xor rcx, rcx\n"
            "mov rdx, 1\n"
            "pop rbx\n"
            "pop rax\n"
            "cmp rax, rbx\n"
            f"cmov{op.operand.name.lower()[0]} rcx, rdx\n"
            "push rcx\n"
        )
    elif op.operand in (Operator.LE, Operator.GE, Operator.NE):
        return (
            "xor rcx, rcx\n"
            "mov rdx, 1\n"
            "pop rbx\n"
            "pop rax\n"
            "cmp rax, rbx\n"
            f"cmov{op.operand.name.lower()} rcx, rdx\n"
            "push rcx\n"
        )
    elif op.operand == Operator.STORE:
        
        return (
            "pop rax\n"
            "pop rbx\n"
            f"{call_npd_code if State.config.re_NPD else ''}"
            "mov [rax], rbx\n"
        )
    elif op.operand == Operator.LOAD:
        return (
            "pop rax\n"
            f"{call_npd_code if State.config.re_NPD else ''}"
            "mov rbx, [rax]\n"
            "push rbx\n"
        )
    elif op.operand == Operator.STORE8:
        return (
            "pop rax\n"
            "pop rbx\n"
            f"{call_npd_code if State.config.re_NPD else ''}"
            "mov [rax], bl\n"
        )
    elif op.operand == Operator.LOAD8:
        return (
            "pop rax\n"
            f"{call_npd_code if State.config.re_NPD else ''}"
            "xor rbx, rbx\n"
            "mov bl, [rax]\n"
            "push rbx\n"
        )
    else:
        cont_assert(False, f"Generation isn't implemented for operator: {op.operand.name}")