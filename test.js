let static_mem = null;

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
        obj.instance.exports.main();
    }
)