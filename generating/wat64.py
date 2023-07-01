import subprocess
import math

from typing import List, Set, Union

from parsing.op import *
from state import *
from type_checking.types import *

assert len(Operator) == 20, "Unimplemented operator in wat64.py"
assert len(OpType) == 40, "Unimplemented type in wat64.py"

WAT64_HEADER =\
"""
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
(func $upcast_move (param i64 i64 i64) (result i64 i64)
    (local.get 1)
    (local.get 2)
    (i64.add) (i32.wrap_i64) 
    (local.get 0)
    (local.get 2)
    (i64.add) (i32.wrap_i64)
    (i64.load) (i64.store)
    (local.get 0)
    (local.get 1))
(func $upcast_set (param i64 i64 i64) (result i64)
    (local.get 1)
    (local.get 2)
    (i64.add) (i32.wrap_i64)
    (local.get 0) (i64.store)
    (local.get 1))
(global $heap_end (mut i64) (i64.const {}))
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

def byte_to_hex_code(byte: int):
    """This can only accept positive integers below 265"""
    return f"\\" + (hex(byte)[2:] if byte >= 16 else '0' + hex(byte)[2:])

def generate_type(t: Type, offset: int, buf: List[Union[int, Type]],
                  queue_set: Set[Type], queue_list: List[Type],
                  types_table: Dict[Type, int]) -> int:
    """Returns new offset"""
    if isinstance(t, Int):
        buf += [State.TYPE_IDS["int"], 8, 1]
        offset += 24
    elif isinstance(t, Ptr):
        if t.typ is None:
            buf += [State.TYPE_IDS["ptr"], 8, 1, 0]
        else:
            if not (t.typ in types_table or t.typ in queue_set):
                queue_set.add(t.typ)
                queue_list.append(t.typ)
            buf += [State.TYPE_IDS["ptr"], 8, 1, t.typ]
        offset += 32
    elif isinstance(t, Array):
        cont_assert(t.len != -1 and t.typ is not None, 
            "In lang(impossible to create by user) array needs to be generated")
        if not (t.typ in types_table or t.typ in queue_set):
            queue_set.add(t.typ)
            queue_list.append(t.typ)
        buf += [State.TYPE_IDS["array"], 8, 1, t.typ, t.len]
        offset += 40
    elif isinstance(t, Addr):
        buf += [State.TYPE_IDS["addr"], 8, 1, offset + 40, offset + 48 + len(t.in_types) * 8]
        for in_type in t.in_types:
            if not (in_type in types_table or in_type in queue_set):
                queue_set.add(in_type)
                queue_list.append(in_type)
            buf.append(in_type)
        buf.append(0)
        for out_type in t.out_types:
            if not (out_type in types_table or out_type in queue_set):
                queue_set.add(out_type)
                queue_list.append(out_type)
            buf.append(out_type)
        buf.append(0)
        offset += 56 + (len(t.in_types) + len(t.out_types)) * 8
    elif isinstance(t, Struct):
        State.curr_type_id += 1
        buf += [State.curr_type_id, sizeof(t), 0]
        if t.parent is not None:
            if not (t.parent in types_table or t.parent in queue_set):
                queue_set.add(t.parent)
                queue_list.append(t.parent)
            buf.append(t.parent)
        else:
            buf.append(0)
        buf.append(offset+40)
        for field in t.fields_types:
            if not (field in types_table or field in queue_set):
                queue_set.add(field)
                queue_list.append(field)
            buf.append(field)
        buf.append(0)
        offset += 48 + len(t.fields_types) * 8
    elif isinstance(t, VarType):
        State.throw_error("Can't get variable type runtime representation")
    return offset

def generate_types(offset: int) -> Tuple[int, str, Dict[Type, int]]:
    initial_offset = offset
    types_table: Dict[Type, int] = {}
    buf: List[Union[int, Type]] = []
    queue_set = State.runtimed_types_set.copy()
    queue_list = State.runtimed_types_list.copy()
    
    while queue_list:
        t = queue_list.pop()
        queue_set.remove(t)
        types_table[t] = offset
        offset = generate_type(t, offset, buf, queue_set, queue_list, types_table)

    text_buf = f"(data (i32.const {initial_offset}) \""
    for byte in buf:
        if isinstance(byte, Type):
            byte = types_table[byte]
        text_buf += "".join(map(byte_to_hex_code, byte.to_bytes(8, "little")))
    text_buf += '")'

    return offset, text_buf, types_table

def generate_data() -> Tuple[int, str, Dict[str, int]]:
    data_table = {}
    buf = ""
    offset = 1
    for index, string in enumerate(State.string_data):
        string_data = "".join(map(byte_to_hex_code, string))
        buf += f'(data (i32.const {offset}) "{string_data}")'
        data_table[f"str_{index}"] = offset
        offset += len(string)

    return (offset, buf, data_table)

def generate_proc_table() -> Tuple[Dict[Proc, int], str]:
    buf = f"(table {len(State.referenced_procs)} funcref) "
    buf += "(elem (i32.const 0)"
    procs_table = {}
    for index, proc in enumerate(State.referenced_procs):
        procs_table[proc] = index
        if proc.is_imported:
            buf += f" ${proc.name}"
        else:
            buf += f" $addr_{proc.ip}"
    return procs_table, buf + ")"

def get_static_size(data_offset: int) -> int:
    return data_offset + Memory.global_offset +\
        State.config.size_call_stack + State.config.size_bind_stack

def generate_globals(data_offset: int) -> str:
    call_stack_offset = data_offset + Memory.global_offset
    bind_stack_offset = call_stack_offset + State.config.size_call_stack
    call_stack = f"(global $call_stack_ptr (mut i32) (i32.const {call_stack_offset}))"
    bind_stack = f"(global $bind_stack_ptr (mut i32) (i32.const {bind_stack_offset}))"

    return call_stack + bind_stack

def generate_imports() -> str:
    buf = ""

    for name, path in State.imported_procs:
        path = " ".join(
            map(lambda x: f'"{x}"',
            path.split(".")))
        param = f"(param{' i64' * len(State.procs[name].in_stack)})"
        result = f"(result{' i64' * len(State.procs[name].out_stack)})"
        buf += f"(import {path} (func ${name} {param} {result}))"

    return buf

def generate_call_types(call_types: List[str]):
    buf = ""
    for index, signature in enumerate(call_types):
        buf += f" (type $call_type_{index} {signature})"
    return buf

def generate_wat64(ops: List[Op]) -> str:
    offset, data, data_table = generate_data()
    procs_table, procs_table_wat = generate_proc_table()
    offset, types_wat, types_table = generate_types(offset)
    buf = "(module " + generate_imports() + WAT64_HEADER.format(
        math.ceil(get_static_size(offset) / MEMORY_PAGE_SIZE),
        get_static_size(offset)
    ) + generate_globals(offset) + data + procs_table_wat + types_wat
    call_types: List[str] = []
    main_buf = '(func (export "main") '
    for op in ops:
        if not op.compiled: continue
        if State.current_proc is not None and State.config.o_UPR:
            if State.current_proc not in State.used_procs:
                if op.type == OpType.ENDPROC:
                    State.current_proc = None
                continue
        
        if State.current_proc is not None or op.type == OpType.DEFPROC:
            buf += generate_op_wat64(op, offset, data_table, procs_table, call_types, types_table)
        else:
            main_buf += generate_op_wat64(op, offset, data_table, procs_table, call_types, types_table)
    buf += generate_call_types(call_types)
    main_buf += ")"
    buf += main_buf + ")"

    return buf

def generate_block_type_info(block: Block) -> str:
    if not block.stack_effect: return ""

    return f"(param{' i64' * block.stack_effect[0]}) (result{' i64' * block.stack_effect[1]})"


def generate_op_wat64(op: Op, offset: int, data_table: Dict[str, int],
                      procs_table: Dict[Proc, int], call_types: List[str],
                      types_table: Dict[Type, int]) -> str:
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
            f"{State.current_proc.memory_size - op.operand}) (i64.sub)"
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
        return f"(i64.const {procs_table[op.operand]})"
    elif op.type == OpType.OPERATOR:
        return generate_operator_wat64(op)
    elif op.type == OpType.SYSCALL:
        State.throw_error("Syscalls are not supported for target wat64")
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
        name = f"$addr_{op.operand.ip}"
        if op.operand.is_exported:
            name += f'(export "{op.operand.name}")'
        params = " i64" * len(op.operand.in_stack)
        results = " i64" * len(op.operand.out_stack)
        allocation = f"(global.get $call_stack_ptr) (i32.const {op.operand.memory_size}) "
        allocation += "(i32.add) (global.set $call_stack_ptr)"
        args = "".join([f"(local.get {i})"
            for i in range(len(op.operand.in_stack))])
        return f"(func {name} (param{params}) (result{results}) {allocation} {args}"
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
        State.bind_stack_size -= op.operand
        return \
            f"(global.get $bind_stack_ptr) (i32.const {op.operand * 8}) (i32.sub) (global.set $bind_stack_ptr)"
    elif op.type == OpType.PUSH_BIND_STACK:
        return \
            f"(global.get $bind_stack_ptr) (i32.const {(State.bind_stack_size - op.operand) * 8}) (i32.sub) (i64.load)"
    elif op.type == OpType.CALL:
        if op.operand.is_imported:
            return f"(call ${op.operand.name})"
        else:
            return f"(call $addr_{op.operand.ip})"
    elif op.type == OpType.TYPED_LOAD:
        return LOAD_CODE
    elif op.type == OpType.PACK:
        assert State.config.struct_malloc[1], "You must have malloc to you this operation on this platform"
        struct = State.structures[op.operand]
        size = sizeof(struct)
        buf = f"(i64.const {size}) "
        if State.procs["malloc"].is_imported:
            buf += f"(call ${State.procs['malloc'].name}) "
        else:
            buf += f"(call $addr_{State.procs['malloc'].ip}) "
        buf += "(call $dup) (i32.const 0) (call $bind) (global.get $bind_stack_ptr) "
        buf += "(i32.const 8) (i32.add) (global.set $bind_stack_ptr) "
        if "__init__" in struct.methods:
            buf += f"(call $addr_{struct.methods['__init__'].ip}) "
            buf += "(global.get $bind_stack_ptr) (i32.const 8) (i32.sub) "
            buf += "(call $dup) (global.set $bind_stack_ptr) (i64.load) "
        else:
            offset = 0
            for index, field in list(enumerate(struct.fields_types))[::-1]:
                offset += sizeof(field)
                if index in struct.defaults:
                    buf += f"(i64.const {struct.defaults[index]}) "

                buf += f"(i64.const {size-offset}) (i64.add) "
                buf += "(call $prepare_store) (i64.store) "
                buf += "(global.get $bind_stack_ptr) (i32.const 8) (i32.sub) (i64.load) "
            buf += "(global.get $bind_stack_ptr) (i32.const 8) (i32.sub) (global.set $bind_stack_ptr)"
        return buf
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
    elif op.type in (OpType.INDEX, OpType.INDEX_PTR):
        return (
            f"(call $swap) (i64.const {op.operand[0]}) (i64.mul) (i64.add) "
            f"{LOAD_CODE if op.type == OpType.INDEX else ''}"
        )
    elif op.type == OpType.PUSH_FIELD:
        return f"(i64.const {op.operand}) (i64.add) {LOAD_CODE}"
    elif op.type == OpType.PUSH_FIELD_PTR:
        return f"(i64.const {op.operand}) (i64.add)"
    elif op.type == OpType.UPCAST:
        assert State.config.struct_malloc[1], "You must have malloc to you this operation on this platform"
        buf = f"(i64.const {op.operand[0]}) "
        if State.procs["malloc"].is_imported:
            buf += f"(call ${State.procs['malloc'].name}) "
        else:
            buf += f"(call $addr_{State.procs['malloc'].ip}) "
        for i in range(op.operand[2] // 8):
            buf += f"(i64.const {i*8}) (call $upcast_move) "
        buf += "(call $swap) (drop)"
        for i in range(op.operand[1]):
            buf += f"(i64.const {op.operand[0]-(i+1)*8}) (call $upcast_set) "
        return buf
    elif op.type == OpType.AUTO_INIT:
        
        if State.current_proc is not None:
            var: Array = State.current_proc.variables[op.operand[0].name]
            memory = (
                "(global.get $call_stack_ptr) (i64.extend_i32_s) "
                f"(i64.const {State.current_proc.memory_size - op.operand[0].offset}) (i64.sub) "
            )
        else:
            var: Array = State.variables[op.operand[0].name]
            memory = f"(i64.const {offset + op.operand[0].offset}) "
        if var.len == 0: return ""
        return (
            f"(i64.const 0) (loop $addr_{op.operand[1]} (param i64) (result i64) "
            f"(call $dup) (i64.const {sizeof(var.typ)}) (i64.mul) {memory} (i64.add) "
            f"(call $swap) (call $dup) (i64.const {sizeof(var.typ.typ)}) (i64.mul) "
            f"(i64.const {sizeof(var)}) (i64.add) {memory} (i64.add) "
            "(call $swap) (call $rot) (call $prepare_store) (i64.store) "
            "(i64.const 1) (i64.add) (call $dup) "
            f"(i64.const {var.len}) (i64.ne) (br_if $addr_{op.operand[1]})) (drop) "
        )
    elif op.type == OpType.CALL_ADDR:
        params = f"(param {' i64' * len(op.operand.in_types)})"
        results = f"(result {'i64' * len(op.operand.out_types)})"
        call_types.append(f"(func {params} {results})")
        return (
            "(i32.wrap_i64) "
            f"(call_indirect (type $call_type_{len(call_types) - 1}))"
        )
    elif op.type == OpType.ASM:
        return f"({op.operand})"
    elif op.type == OpType.PUSH_TYPE:
        return f"(i64.const {types_table[op.operand]})"
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