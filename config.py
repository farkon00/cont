import argparse
import json
import os

class Config:
    DESCRIPTIONS: dict[str, str] = {
        "program" : "The program to compile and optionally run",
        "run" : "Run program after compilation",
        "dump" : "Dump operations without compilation",
        "dump_tokens" : "Dump tokens without parsing or compilating",
        "out" : "The output executable file and name for .asm file",
        "config" : "Config file",
        "stdout" : "File to output stdout of complier and program",
        "input" : "Stdin for program",
        "error" : "Stderr for program",
    }

    BOOL_OPTIONS: dict[str, tuple[list[str], bool]] = {
        "run" : (["-r", "-run"], False),
        "dump" : (["-d", "-dump"], False),
        "dump_tokens" : (["-dt", "-dump-tokens"], False),
    }

    def __init__(self, argv):
        self.args = self.setup_args_parser().parse_args(argv[1:])
        self.config = self.load_config(self.args.config)

    def setup_args_parser(self):
        args_parser = argparse.ArgumentParser()

        args_parser.add_argument("program", help=self.DESCRIPTIONS["program"])

        args_parser.add_argument("-o", "--out", default=None, dest="out", help=self.DESCRIPTIONS["out"])
        args_parser.add_argument("-c", "--config", default=None, dest="config", help=self.DESCRIPTIONS["config"])
        args_parser.add_argument("-stdo", "--stdout", dest="stdout", default=None, help=self.DESCRIPTIONS["stdout"])
        args_parser.add_argument("-i", "--input", dest="input", default=None, help=self.DESCRIPTIONS["input"])
        args_parser.add_argument("-e", "--error", dest="error", default=None, help=self.DESCRIPTIONS["error"])

        for name, i in self.BOOL_OPTIONS.items():
            args_parser.add_argument(*i[0], action="store_true", default=i[1], dest=name, help=self.DESCRIPTIONS[name])

        return args_parser

    def load_config(self, config_file):
        if config_file is None:
            if "cont_build.json" in os.listdir():
                return self.load_config("cont_build.json")
            return {}

        with open(config_file, "r") as f:
            return json.load(f)

    @property
    def program(self): return self.args.program

    @property
    def run(self): return self.args.run

    @property
    def dump(self): return self.args.dump

    @property
    def dump_tokens(self): return self.args.dump_tokens

    @property
    def out(self): return self.config.get("out", self.args.out)

    @property
    def stdout(self): return self.config.get("stdout", self.args.stdout)

    @property
    def input(self): return self.config.get("input", self.args.input)

    @property
    def error(self): return self.config.get("error", self.args.error)