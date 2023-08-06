let static_mem = null;
let wasm_exports = null;

function ContExitException(message) {
    const error = new Error(message);
    error.name = "ContExitException";
    return error;
}
ContExitException.prototype = Object.create(Error.prototype);

function bnToBuf(bn) {
    var hex = BigInt(bn).toString(16);
    hex = "0".repeat(16 - hex.length) + hex;
  
    var len = hex.length / 2;
    var u8 = new Uint8Array(len);
  
    var i = 0;
    var j = 14;
    while (i < len) {
      u8[i] = parseInt(hex.slice(j, j+2), 16);
      i += 1;
      j -= 2;
    }
  
    return u8;
}
function bufToBn(arr) {
    let result = BigInt(0);
    for (let i = arr.length - 1; i >= 0; i--) {
        result = result * BigInt(256) + BigInt(arr[i]);
    }
    return result;
}
function load_string(length, offset) {
    const bytes = new Uint8Array(static_mem.buffer, Number(offset), Number(length));
    return new TextDecoder("utf8").decode(bytes);
}

function load_object(offset) {
    offset = Number(offset);
    const type = bufToBn(new Uint8Array(static_mem.buffer, offset, 8));
    if (type == 0) // Int
        return Number(bufToBn(new Uint8Array(static_mem.buffer, offset + 8, 8)));
    else if (type == 1) { // String
        const length = Number(bufToBn(new Uint8Array(static_mem.buffer, offset + 8, 8)));
        const ptr = Number(bufToBn(new Uint8Array(static_mem.buffer, offset + 16, 8)));
        return load_string(length, ptr);
    }
    else if (type == 2) // Null
        return null;
    else if (type == 3) // Undefined
        return undefined;
    else if (type == 4) { // Array
        const length = Number(bufToBn(new Uint8Array(static_mem.buffer, offset + 8, 8)));
        const ptr = Number(bufToBn(new Uint8Array(static_mem.buffer, offset + 16, 8)));
        let res = [];
        for (let i = 0; i < length; i++) {
            let elem_ptr = Number(bufToBn(new Uint8Array(static_mem.buffer, ptr + i * 8, 8)));
            res.push(load_object(elem_ptr));
        }
        return res;
    }
    else if (type == 5) // Object
        return serialized_objects[Number(bufToBn(new Uint8Array(static_mem.buffer, offset + 8, 8)))];
}
function upload_object(obj) {
    const mem_buf = new Uint8Array(static_mem.buffer);
    let result_ptr = 0n;
    if (typeof obj === "number" && obj % 1 == 0) {
        result_ptr = wasm_exports.malloc(BigInt(16));
        mem_buf[Number(result_ptr)] = 0; // Type
        mem_buf.set(bnToBuf(BigInt(obj)), Number(result_ptr) + 8); // Value
    }
    else if (typeof obj === "string") {
        result_ptr = wasm_exports.malloc(BigInt(24));
        const bytes = new TextEncoder().encode(string);
        mem_buf[Number(result_ptr)] = 1; // Type
        mem_buf.set(bnToBuf(BigInt(bytes.length)), Number(result_ptr) + 8); // Length
        const string_ptr = wasm_exports.malloc(BigInt(bytes.length));
        mem_buf.set(bytes, Number(string_ptr)) // String
        mem_buf.set(bnToBuf(string_ptr), Number(result_ptr) + 16); // String ptr
    }
    else if (obj === null) {
        result_ptr = wasm_exports.malloc(BigInt(8));
        mem_buf[Number(result_ptr)] = 2; // Type
    }
    else if (obj === undefined || (typeof obj === "number" && obj % 1 != 0)) {
        result_ptr = wasm_exports.malloc(BigInt(8));
        mem_buf[Number(result_ptr)] = 3; // Type
    }
    else if (Array.isArray(obj)) {
        result_ptr = wasm_exports.malloc(BigInt(24));
        mem_buf[Number(result_ptr)] = 4; // Type
        mem_buf.set(bnToBuf(BigInt(obj.length)), Number(result_ptr) + 8); // Length
        const array_ptr = wasm_exports.malloc(BigInt(8 * obj.length));
        for (let i = 0; i < obj.length; i++) {
            mem_buf.set(bnToBuf(upload_object(obj[i])), Number(array_ptr) + 8 * i);
        }
        mem_buf.set(bnToBuf(BigInt(array_ptr)), Number(result_ptr) + 16); // Array pointer
    } 
    else {
        result_ptr = wasm_exports.malloc(BigInt(16));
        mem_buf[Number(result_ptr)] = 5; // Type
        serialized_objects[serialized_objects_count++] = obj;
        mem_buf.set(bnToBuf(BigInt(serialized_objects_count - 1)), Number(result_ptr) + 8); // ID
    }
    return result_ptr;
}

let puts_buffer = "";
const testImport = {
    "cont_runtime": {
        exit(code) {
            throw ContExitException("Cont exited with exit code " + code);
        },
        timesys(ptr) {
            const time = BigInt(Math.round(Date.now() / 1000));
            if (ptr != 0)
                new Uint8Array(static_mem.buffer).set(bnToBuf(time), Number(ptr));
            return time;
        },
        println(length, offset) {
            const bytes = new Uint8Array(static_mem.buffer, Number(offset), Number(length));
            const string = new TextDecoder("utf8").decode(bytes);
            console.log(puts_buffer + string);
            puts_buffer = "";
        },
        puts(length, offset) {
            const bytes = new Uint8Array(static_mem.buffer, Number(offset), Number(length));
            const string = new TextDecoder("utf8").decode(bytes);
            const lines = string.split("\n");
            for (let i = 0; i < lines.length - 1; i++) {
                if (i == 0) {
                    console.log(puts_buffer + lines[i]);
                    puts_buffer = "";
                } else console.log(lines[i]);
            }
            puts_buffer += lines[lines.length - 1];
        }
    }
};

const fs = require("fs");
const process = require("process");

let wasm_bytes = fs.readFileSync("tests/temp/code_" + process.argv[2] + ".wasm");

WebAssembly.instantiate(wasm_bytes, testImport).then(
    (obj) => {
        static_mem = obj.instance.exports.memory;
        wasm_exports = obj.instance.exports;
        obj.instance.exports.main();
    }
)