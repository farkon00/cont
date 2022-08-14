import argparse

class Config:
    def __init__(self, argv):
        self.args = self.setup_args_parser().parse_args(argv[1:])

    def setup_args_parser(self):
        args_parser = argparse.ArgumentParser()
        args_parser.add_argument("program", help="The program to compile and optionally run")
        args_parser.add_argument("-o", "--out", default=None, dest="out", 
            help="The output executable file and name for .asm file")
        args_parser.add_argument("-r", "--run", action="store_true", default=False, dest="run", 
            help="Run program after compilation")
        args_parser.add_argument("--dump", action="store_true", default=False, dest="dump", 
            help="Dump opeartions without compilation")
        args_parser.add_argument("--dump-tokens", action="store_true", default=False, dest="dump_tokens", 
            help="Dump tokens without parsing or compilating")
        args_parser.add_argument("-stdo", "--stdout", dest="stdout", default=None, 
            help="File to output stdout of complier and program")
        args_parser.add_argument("-i", "--input", dest="input", default=None, 
            help="Stdin for program")
        args_parser.add_argument("-e", "--error", dest="error", default=None, 
            help="Stderr for program")

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