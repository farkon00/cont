import json
import sys
import io
import traceback
from typing import Any

import cont
from state import State

class StdIOWrapper(io.TextIOBase):
    OVERWRITTEN = ["close", "__getattribute__", "__setattr__", "__delattr__"]

    def __init__(self, real_io: io.TextIOBase):
        object.__setattr__(self, "real_io", real_io)

    def close(): pass

    def __getattribute__(self, name: str) -> Any:
        if name in object.__getattribute__(self, "OVERWRITTEN"):
            return object.__getattribute__(self, name)
        return getattr(object.__getattribute__(self, "real_io"), name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        if name in object.__getattribute__(self, "OVERWRITTEN"):
            return object.__setattr__(self, name, value)
        return setattr(object.__getattribute__(self, "real_io"), name, value)
    
    def __delattr__(self, name: str) -> None:
        if name in object.__getattribute__(self, "OVERWRITTEN"):
            return object.__delattr__(self, name)
        return delattr(object.__getattribute__(self, "real_io"), name)

def mock_throw_error(error: str, do_exit: bool = True):
    assert False, error

def main():
    orig_throw_error = State.throw_error
    orig_stdout = sys.stdout
    sys.stdin = StdIOWrapper(sys.stdin)
    sys.stderr = StdIOWrapper(sys.stderr)
    while True:
        try:
            command = json.loads(input())
            if command["type"] == "check_errors":
                try:
                    State.throw_error = mock_throw_error
                    sys.stdout = io.StringIO()
                    State.full_reset()
                    sys.argv = ["cont.py", command["file"]]
                    cont.main(lsp_mode=True)
                    sys.stdout = orig_stdout
                    print('{"success": true, "has_error": false}', flush=True)
                except AssertionError as e:
                    # Not using split, because file names might include a colon and maxsplit works from the left
                    char_begin = State.loc.rfind(":")
                    char = int(State.loc[char_begin+1:]) - 1
                    line_begin = State.loc.rfind(":", 0, char_begin)
                    line = int(State.loc[line_begin+1:char_begin]) - 1
                    sys.stdout = orig_stdout
                    print(json.dumps({
                        "success": True, "has_error": True, "error_message": e.args[0],
                        "file": State.abs_path, "line": line, "char": char
                    }), flush=True)
                except SystemExit:
                    value = sys.stdout.getvalue()
                    sys.stdout = orig_stdout
                    index = value.find("\033[")
                    while index != -1:
                        end_index = value.find("m", index)
                        value = value[:index] + value[end_index + 1:]
                        index = value.find("\033[")
                    print(json.dumps({
                        "success": False, "display": True,
                        "error": value
                    }), flush=True)
            else:
                print('{"success": false, "display": false, "error": "Command type not supported"}', flush=True)
        except Exception as e:
            sys.stdout = orig_stdout
            print(json.dumps({
                "success": False, "display": False,
                "error": f"Unhandled exception in the lsp: {traceback.format_exc()}"
            }), flush=True)
        State.throw_error = orig_throw_error

if __name__ == "__main__":
    main()