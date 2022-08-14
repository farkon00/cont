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

    REGULAR_OPTIONS: dict[str, list[str]] = {
        "out" : ["-o", "--out"],
        "stdout" : ["-stdo", "--stdout"],
        "input" : ["-i", "--input"],
        "error" : ["-e", "--error"],
    }

    CONFIG_BOOL_OPTIONS: dict[str, bool] = {
        "re_IOR" : True,
    }

    def __init__(self, argv):
        self.args = self.setup_args_parser().parse_args(argv[1:])
        self.config = self.load_config(self.args.config)
        self.define_properties()

    def setup_args_parser(self):
        args_parser = argparse.ArgumentParser()

        args_parser.add_argument("program", help=self.DESCRIPTIONS["program"])
        args_parser.add_argument("-c", "--config", default=None, dest="config", help=self.DESCRIPTIONS["config"])

        for name, i in self.BOOL_OPTIONS.items():
            args_parser.add_argument(*i[0], action="store_true", default=i[1], dest=name, help=self.DESCRIPTIONS[name])

        for name, args in self.REGULAR_OPTIONS.items():
            args_parser.add_argument(*args, default=None, dest=name, help=self.DESCRIPTIONS[name])

        return args_parser

    def load_config(self, config_file):
        if config_file is None:
            if "cont_build.json" in os.listdir():
                return self.load_config("cont_build.json")
            return {}

        with open(config_file, "r") as f:
            return json.load(f)

    def define_properties(self):
        for name in self.BOOL_OPTIONS:
            setattr(self.__class__, name, property(fget=lambda self, name=name : getattr(self.args, name)))

        for name in self.REGULAR_OPTIONS:
            setattr(self.__class__, name, property(fget=lambda self, name=name : \
                self.config.get(name, getattr(self.args, name))))

        for name, default in self.CONFIG_BOOL_OPTIONS.items():
            setattr(self.__class__, name, property(fget=lambda self, name=name : self.config.get(name, default)))

    @property
    def program(self): return self.args.program