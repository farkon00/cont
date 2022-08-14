import argparse

class Config:
    DESCRIPTIONS: dict[str, str] = {
        "program" : "The program to compile and optionally run",
        "run" : "Run program after compilation",
        "dump" : "Dump operations without compilation",
        "dump_tokens" : "Dump tokens without parsing or compilating",
        "o" : "The output executable file and name for .asm file",
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

    def setup_args_parser(self):
        args_parser = argparse.ArgumentParser()
        
        args_parser.add_argument("program", help=self.DESCRIPTIONS["program"])

        args_parser.add_argument("-o", "--out", default=None, dest="out", help=self.DESCRIPTIONS["o"])
        args_parser.add_argument("-stdo", "--stdout", dest="stdout", default=None, help=self.DESCRIPTIONS["stdout"])
        args_parser.add_argument("-i", "--input", dest="input", default=None, help=self.DESCRIPTIONS["input"])
        args_parser.add_argument("-e", "--error", dest="error", default=None, help=self.DESCRIPTIONS["error"])

        for name, i in self.BOOL_OPTIONS.items():
            args_parser.add_argument(*i[0], action="store_true", default=i[1], dest=name, help=self.DESCRIPTIONS[name])

        return args_parser

    @property
    def program(self): return self.args.program
    
    @property
    def out(self): return self.args.out

    @property
    def run(self): return self.args.run

    @property
    def dump(self): return self.args.dump

    @property
    def dump_tokens(self): return self.args.dump_tokens

    @property
    def stdout(self): return self.args.stdout

    @property
    def input(self): return self.args.input

    @property
    def error(self): return self.args.error