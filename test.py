import os
import subprocess
import pytest

tests = os.listdir("tests")

try:
    os.mkdir("tests/results")
except FileExistsError:
    tests.remove("results")
try:
    os.mkdir("tests/temp")
except FileExistsError:
    tests.remove("temp")

if subprocess.getstatusoutput("fasm -v")[0] == 0: # Check if fasm is installed
    print("Please install Flat Assembler (Fasm)")
    exit(1)

@pytest.mark.parametrize("test_name", tests)
def test(test_name):
    with open(f"tests/{test_name}", "r") as f:
        test = f.read()

    parts = test.split("\n:\n")

    with open(f"tests/temp/code_{test_name}.cn", "w") as f:
        f.write(parts[0])
    with open(f"tests/temp/stdin_{test_name}", "w") as f:
        if len(parts) > 2:
            f.write(parts[2])
    exp_stdout = parts[1]
    if len(parts) > 3:
        exp_stderr = parts[3].format(source_file=f"tests/temp/code_{test_name}")
    else:
        exp_stderr = ""

    subprocess.run(
        [
            "python", "cont.py", f"tests/temp/code_{test_name}.cn",
            "-t", "fasm_x86_64_linux",
            "-i", f"tests/temp/stdin_{test_name}",
            "-e", f"tests/results/{test_name}_stderr",
            "--stdout", f"tests/results/{test_name}_stdout",
            "-r",
        ]
    )

    os.remove(f"tests/temp/code_{test_name}.cn")
    os.remove(f"tests/temp/stdin_{test_name}")
    try:
        os.remove(f"tests/temp/code_{test_name}.asm")
        os.remove(f"tests/temp/code_{test_name}")
    except FileNotFoundError:
        pass

    with open(f"tests/results/{test_name}_stdout", "r") as f:
        stdout = f.read()

    with open(f"tests/results/{test_name}_stderr", "r") as f:
        stderr = f.read()

    assert stdout == exp_stdout
    assert stderr == exp_stderr

if subprocess.getstatusoutput("node -v")[0] != 0:
    print("[OPTIONAL] Cannot run tests for wasm, please install node.js.")
else:
    @pytest.mark.parametrize("test_name", tests)
    def test_node_wat64(test_name):
        with open(f"tests/{test_name}", "r") as f:
            test = f.read()

        parts = test.split("\n:\n")

        with open(f"tests/temp/code_{test_name}_wasm.cn", "w") as f:
            f.write(parts[0])
        with open(f"tests/temp/stdin_{test_name}_wasm", "w") as f:
            if len(parts) > 2:
                f.write(parts[2])
        exp_stdout = parts[1]
        if len(parts) > 3:
            exp_stderr = parts[3].format(source_file=f"tests/temp/code_{test_name}_wasm")
        else:
            exp_stderr = ""

        subprocess.run(
            [
                "python", "cont.py", f"tests/temp/code_{test_name}_wasm.cn",
                "-t", "wat64",
                "-o", f"tests/temp/code_{test_name}",
                "-e", f"tests/results/{test_name}_stderr_wasm",
                "--stdout", f"tests/results/{test_name}_stdout_wasm",
            ]
        )
        if os.path.isfile(f"tests/temp/code_{test_name}.wasm"):
            with open(f"tests/results/{test_name}_stdout_wasm", "a") as stdout:
                with open(f"tests/results/{test_name}_stderr_wasm", "a") as stderr:
                    with open(f"tests/temp/stdin_{test_name}_wasm", "r") as stdin:
                        subprocess.run(
                            ["node", "test.js", test_name],
                            stdout=stdout, stderr=stderr, stdin=stdin
                        )

        os.remove(f"tests/temp/code_{test_name}_wasm.cn")
        os.remove(f"tests/temp/stdin_{test_name}_wasm")
        try:
            os.remove(f"tests/temp/code_{test_name}.wat")
            os.remove(f"tests/temp/code_{test_name}.wasm")
        except FileNotFoundError:
            pass

        with open(f"tests/results/{test_name}_stdout_wasm", "r") as f:
            stdout = f.read()

        with open(f"tests/results/{test_name}_stderr_wasm", "r") as f:
            stderr = f.read()

        assert stdout == exp_stdout
        assert stderr == exp_stderr