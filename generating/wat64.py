import subprocess
import math

from typing import List

from parsing.op import *
from state import *

assert len(Operator) == 20, "Unimplemented operator in wat64.py"
assert len(OpType) == 40, "Unimplemented type in wat64.py"

# TODO: make an import syntax
WAT64_HEADER =\
"""
(import "console" "log" (func $__js_log (param i64)))
(memory $static_memory {})
(export "static_memory" (memory $static_memory))
(func $div (param i64 i64) (result i64 i64)
    (local.get 0)
    (local.get 1)
    (i64.div_s)
    (local.get 0)
    (local.get 1)
    (i64.rem_s))
(func $dup (param i64) (result i64 i64)
    (local.get 0)
    (local.get 0))
(func $swap (param i64 i64) (result i64 i64)
    (local.get 1)
    (local.get 0))
(func $rot (param i64 i64 i64) (result i64 i64 i64)
    (local.get 2)
    (local.get 1)
    (local.get 0))
(func $over (param i64 i64) (result i64 i64 i64)
    (local.get 0)
    (local.get 1)
    (local.get 0))
(func $prepare_store (param i64 i64) (result i32 i64)
    (local.get 1)
    (i32.wrap_i64)
    (local.get 0))
""".replace("\n", "").replace("    ", "")
LOAD_CODE = "(i32.wrap_i64) (i64.load)"
MEMORY_PAGE_SIZE = 65536 

def compile_ops_wat64(ops: List[Op]):
    if State.config.run:
        print("Can't use run flag for this target")
        exit(1)
    if subprocess.getstatusoutput("wat2wasm --version")[0] != 0:
        print("Please install wabt and wat2wasm specifically.")
        exit(1)
    
    out = State.filename if State.config.out is None else State.config.out

    with open(f"{out}.wat", "w") as f:
        f.write(generate_wat64(ops))

    subprocess.run(["wat2wasm", f"{out}.wat"], stdin=sys.stdin, stderr=sys.stderr)

def generate_wat64(ops: List[Op]):
    buf = "(module " + WAT64_HEADER.format(
        math.ceil((Memory.global_offset + 1) / MEMORY_PAGE_SIZE)
    )
    main_buf = '(func (export "main") '
    for op in ops:
        if not op.compiled: continue
        if State.current_proc is not None and State.config.o_UPR:
            if State.current_proc not in State.used_procs:
                if op.type == OpType.ENDPROC:
                    State.current_proc = None
                continue
        
        if State.current_proc is not None or op.type == OpType.DEFPROC:
            buf += generate_op_wat64(op)
        else:
            main_buf += generate_op_wat64(op)
    
    main_buf += ")"
    buf += main_buf + ")"

    return buf

def generate_block_type_info(block : Block) -> str:
    if not block.stack_effect: return ""

    return f"(param{' i64' * block.stack_effect[0]}) (result{' i64' * block.stack_effect[1]})"


def generate_op_wat64(op: Op):
    if op.type == OpType.PUSH_INT:
        return f"(i64.const {op.operand})"
    elif op.type == OpType.PUSH_MEMORY:
        return f"(i64.const {op.operand})"
    elif op.type == OpType.PUSH_VAR:
        return f"(i32.const {State.memories[op.operand].offset + 1}) (i64.load)"
    elif op.type == OpType.PUSH_VAR_PTR:
        return f"(i64.const {State.memories[op.operand].offset + 1})"
    elif op.type == OpType.PUSH_LOCAL_MEM:
        cont_assert(False, "Not implemented op: PUSH_LOCAL_MEM")
    elif op.type == OpType.PUSH_LOCAL_VAR:
        cont_assert(False, "Not implemented op: PUSH_LOCAL_VAR")
    elif op.type == OpType.PUSH_LOCAL_VAR_PTR:
        cont_assert(False, "Not implemented op: PUSH_LOCAL_VAR_PTR")
    elif op.type == OpType.PUSH_STR:
        cont_assert(False, "Not implemented op: PUSH_STR")
    elif op.type == OpType.PUSH_NULL_STR:
        cont_assert(False, "Not implemented op: PUSH_NULL_STR")
    elif op.type == OpType.PUSH_PROC:
        cont_assert(False, "Not implemented op: PUSH_PROC")
    elif op.type == OpType.OPERATOR:
        return generate_operator_wat64(op)
    elif op.type == OpType.SYSCALL:
        cont_assert(False, "Not implemented op: SYSCALL")
    elif op.type == OpType.IF:
        if State.ops_by_ips[op.operand.end].type == OpType.ELSE:
            type_info = generate_block_type_info(State.ops_by_ips[op.operand.end].operand)
        else:
            type_info = generate_block_type_info(op.operand)
        return f"(i64.const 0) (i64.ne) (if {type_info} (then"
    elif op.type == OpType.ELSE:
        return f") (else"
    elif op.type == OpType.ENDIF:
        return "))"
    elif op.type == OpType.WHILE:
        type_info = generate_block_type_info(State.ops_by_ips[op.operand.end].operand)
        return f"(i64.const 0) (i64.ne) (if {type_info} (then (loop $addr_{op.operand.start} {type_info}"
    elif op.type == OpType.ENDWHILE:
        return f"(i64.const 0) (i64.ne) (br_if $addr_{op.operand.start}))))"
    elif op.type == OpType.DEFPROC:
        State.current_proc = op.operand
        if op.operand not in State.used_procs and State.config.o_UPR:
            return ""
        params = " i64" * len(op.operand.in_stack)
        results = " i64" * len(op.operand.out_stack)
        args = "".join([f"(local.get {i})" 
            for i in range(len(op.operand.in_stack))])
        return f"(func $addr_{op.operand.ip} (param{params}) (result{results}) {args}"
    elif op.type == OpType.ENDPROC:
        cont_assert(State.current_proc is not None, "Bug in parsing of procedures")
        State.current_proc = None
        return ")"
    elif op.type == OpType.BIND:
        cont_assert(False, "Not implemented op: BIND")
    elif op.type == OpType.UNBIND:
        cont_assert(False, "Not implemented op: UNBIND")
    elif op.type == OpType.PUSH_BIND_STACK:
        cont_assert(False, "Not implemented op: PUSH_BIND_STACK")
    elif op.type == OpType.CALL:
        return f"(call $addr_{op.operand.ip})"
    elif op.type == OpType.TYPED_LOAD:
        return LOAD_CODE
    elif op.type == OpType.PACK:
        cont_assert(False, "Not implemented op: PACK")
    elif op.type == OpType.UNPACK:
        cont_assert(False, "Not implemented op: UNPACK")
    elif op.type == OpType.MOVE_STRUCT:
        cont_assert(False, "Not implemented op: MOVE_STRUCT")
    elif op.type == OpType.PUSH_FIELD:
        cont_assert(False, "Not implemented op: PUSH_FIELD")
    elif op.type == OpType.PUSH_FIELD_PTR:
        cont_assert(False, "Not implemented op: PUSH_FIELD_PTR")
    elif op.type == OpType.UPCAST:
        cont_assert(False, "Not implemented op: UPCAST")
    elif op.type == OpType.AUTO_INIT:
        cont_assert(False, "Not implemented op: AUTO_INIT")
    elif op.type == OpType.CALL_ADDR:
        cont_assert(False, "Not implemented op: CALL_ADDR")
    elif op.type == OpType.ASM:
        return "(" + op.operand + ")"
    elif op.type == OpType.PUSH_TYPE:
        cont_assert(False, "Not implemented op: PUSH_TYPE")
    elif op.type == OpType.CAST:
        return ""  # Casts are type checking thing
    else:
        cont_assert(False, f"Generation isnt implemented for op type: {op.type.name}")

def generate_operator_wat64(op: Op):
    cont_assert(len(Operator) == 20, "Unimplemented operator in generate_operator_wat64")
    cont_assert(op.type == OpType.OPERATOR, f"generate_operator_wat64 cant generate {op.type.name}")

    if op.operand in (Operator.ADD, Operator.SUB, Operator.MUL):
        return f"(i64.{op.operand.name.lower()})"
    elif op.operand in (Operator.NE, Operator.EQ):
        return f"(i64.{op.operand.name.lower()})(i64.extend_i32_s)"
    elif op.operand in (Operator.LE, Operator.GE, Operator.LT, Operator.GT):
        return f"(i64.{op.operand.name.lower()}_s)(i64.extend_i32_s)"
    elif op.operand == Operator.DROP:
        return f"(drop)"
    elif op.operand == Operator.LOAD:
        return LOAD_CODE
    elif op.operand == Operator.LOAD8:
        return f"(i32.wrap_i64) (i64.load8_u)"
    elif op.operand in (Operator.STORE, Operator.STORE8):
        return f"(call $prepare_store) (i64.{op.operand.name.lower()})"
    else:
        return f"(call ${op.operand.name.lower()})"