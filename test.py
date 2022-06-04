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

@pytest.mark.parametrize("test_name", tests)
def test(test_name):
    with open(f"tests/{test_name}", "r") as f:
        test = f.read()
    
    parts = test.split("\n:\n")

    with open("tests/temp/code.cn", "w") as f:
        f.write(parts[0])
    with open("tests/temp/stdin", "w") as f:
        if len(parts) > 2:
            f.write(parts[2])
    exp_stdout = parts[1]
    if len(parts) > 3:
        exp_stderr = parts[3]
    else:
        exp_stderr = ""

    subprocess.run(["python", "cont.py", "tests/temp/code.cn", "-i", "tests/temp/stdin", "-e",
                    f"tests/results/{test_name}_stderr", "-o", f"tests/results/{test_name}_stdout", "-r"])

    with open(f"tests/results/{test_name}_stdout", "r") as f:
        stdout = f.read()

    with open(f"tests/results/{test_name}_stderr", "r") as f:
        stderr = f.read()

    assert stdout == exp_stdout
    assert stderr == exp_stderr