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
(import "console" "puts" (func $__js_puts (param i64 i64)))
(memory $memory {})
(export "memory" (memory $memory))
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
(func $bind (param i64 i32)
    (global.get $bind_stack_ptr)
    (local.get 1)
    (i32.add)
    (local.get 0)
    (i64.store))
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

def generate_data() -> Tuple[int, str, Dict[str, int]]:
    data_table = {}
    buf = ""
    offset = 1
    for index, string in enumerate(State.string_data):
        string_data = "".join([f"\\{hex(i)[2:] if i >= 16 else '0' + hex(i)[2:]}" for i in string])
        buf += f'(data (i32.const {offset}) "{string_data}")'
        data_table[f"str_{index}"] = offset
        offset += len(string)

    return (offset, buf, data_table)

def get_static_size(data_offset: int) -> int:
    return data_offset + Memory.global_offset +\
        State.config.size_call_stack + State.config.size_bind_stack

def generate_globals(data_offset: int) -> str:
    call_stack_offset = data_offset + Memory.global_offset
    bind_stack_offset = call_stack_offset + State.config.size_call_stack
    call_stack = f"(global $call_stack_ptr (mut i32) (i32.const {call_stack_offset}))"
    bind_stack = f"(global $bind_stack_ptr (mut i32) (i32.const {bind_stack_offset}))"

    return call_stack + bind_stack

def generate_wat64(ops: List[Op]) -> str:
    offset, data, data_table = generate_data()
    buf = "(module " + WAT64_HEADER.format(
        math.ceil(get_static_size(offset) / MEMORY_PAGE_SIZE)
    ) + generate_globals(offset) + data
    main_buf = '(func (export "main") '
    for op in ops:
        if not op.compiled: continue
        if State.current_proc is not None and State.config.o_UPR:
            if State.current_proc not in State.used_procs:
                if op.type == OpType.ENDPROC:
                    State.current_proc = None
                continue
        
        if State.current_proc is not None or op.type == OpType.DEFPROC:
            buf += generate_op_wat64(op, offset, data_table)
        else:
            main_buf += generate_op_wat64(op, offset, data_table)
    
    main_buf += ")"
    buf += main_buf + ")"

    return buf

def generate_block_type_info(block : Block) -> str:
    if not block.stack_effect: return ""

    return f"(param{' i64' * block.stack_effect[0]}) (result{' i64' * block.stack_effect[1]})"


def generate_op_wat64(op: Op, offset: int, data_table: Dict[str, int]) -> str:
    if op.type == OpType.PUSH_INT:
        return f"(i64.const {op.operand})"
    elif op.type == OpType.PUSH_MEMORY:
        return f"(i64.const {offset + op.operand})"
    elif op.type == OpType.PUSH_VAR:
        return f"(i32.const {offset + State.memories[op.operand].offset}) (i64.load)"
    elif op.type == OpType.PUSH_VAR_PTR:
        return f"(i64.const {offset + State.memories[op.operand].offset})"
    elif op.type == OpType.PUSH_LOCAL_MEM:
        return "(global.get $call_stack_ptr) (i64.extend_i32_u) (i64.const " +\
            f"{State.current_proc.memory_size + op.operand + 8}) (i64.sub)"
    elif op.type == OpType.PUSH_LOCAL_VAR:
        var_offset = State.current_proc.memory_size - State.current_proc.memories[op.operand].offset
        return "(global.get $call_stack_ptr)" +\
            f"(i32.const {var_offset}) (i32.sub) (i64.load)"
    elif op.type == OpType.PUSH_LOCAL_VAR_PTR:
        var_offset = State.current_proc.memory_size - State.current_proc.memories[op.operand].offset
        return f"(global.get $call_stack_ptr) (i64.extend_i32_u) (i64.const {var_offset}) (i64.sub)"
    elif op.type == OpType.PUSH_STR:
        return \
            f"(i64.const {len(State.string_data[op.operand])}) (i64.const {data_table[f'str_{op.operand}']})"
    elif op.type == OpType.PUSH_NULL_STR:
        return f"(i64.const {data_table[f'str_{op.operand}']})"
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
        allocation = f"(global.get $call_stack_ptr) (i32.const {op.operand.memory_size}) "
        allocation += "(i32.add) (global.set $call_stack_ptr)"
        args = "".join([f"(local.get {i})"
            for i in range(len(op.operand.in_stack))])
        return f"(func $addr_{op.operand.ip} (param{params}) (result{results}) {allocation} {args}"
    elif op.type == OpType.ENDPROC:
        cont_assert(State.current_proc is not None, "Bug in parsing of procedures")
        State.current_proc = None
        memory_size = State.ops_by_ips[op.operand.start].operand.memory_size
        return f"(global.get $call_stack_ptr) (i32.const {memory_size})" +\
            "(i32.sub) (global.set $call_stack_ptr))"
    elif op.type == OpType.BIND:
        buf = ""
        State.bind_stack_size += op.operand
        for i in range(op.operand):
            buf += f"(i32.const {(op.operand - i - 1) * 8}) (call $bind)"
        buf += f"(global.get $bind_stack_ptr) (i32.const {op.operand * 8}) "
        buf += "(i32.add) (global.set $bind_stack_ptr)"
        return buf
    elif op.type == OpType.UNBIND:
        return \
            f"(global.get $bind_stack_ptr) (i32.const {op.operand * 8}) (i32.sub) (global.set $bind_stack_ptr)"
    elif op.type == OpType.PUSH_BIND_STACK:
        return \
            f"(global.get $bind_stack_ptr) (i32.const {(State.bind_stack_size - op.operand) * 8}) (i32.sub) (i64.load)"
    elif op.type == OpType.CALL:
        return f"(call $addr_{op.operand.ip})"
    elif op.type == OpType.TYPED_LOAD:
        return LOAD_CODE
    elif op.type == OpType.PACK:
        cont_assert(False, "Not implemented op: PACK")
    elif op.type == OpType.UNPACK:
        buf = ""
        for _ in range(op.operand // 8):
            buf += f"(call $dup) {LOAD_CODE} (call $swap) (i64.const 8) (i64.add) "
        return buf + "(drop)"
    elif op.type == OpType.MOVE_STRUCT:
        buf = ""
        for _ in range(op.operand // 8):
            buf += f"(call $over) {LOAD_CODE} (call $over) "
            buf += "(call $prepare_store) (i64.store) "
            buf += "(call $swap) (i64.const 8) (i64.add) " * 2
        return buf + "(drop) (drop)"
    elif op.type == OpType.PUSH_FIELD:
        return f"(i64.const {op.operand}) (i64.add) {LOAD_CODE}"
    elif op.type == OpType.PUSH_FIELD_PTR:
        return f"(i64.const {op.operand}) (i64.add)"
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

def generate_operator_wat64(op: Op) -> str:
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