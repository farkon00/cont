import argparse
import json
import os

from generating.generating import TARGETS

from typing import Any, Dict, List, Tuple, Optional 


class Config:
    """
    A finalized configuration for the compiler run.
    
    The object deals with loading in all the options from different source,
    verifying them and deciding what is the final value of the option.

    The lsp_mode constructor argument indicates whether the compile is
    being run from a CLI or via a function call to the entry point.
    """
    DESCRIPTIONS: Dict[str, str] = {
        "program" : "The program to compile and optionally run",
        "run" : "Run program after compilation",
        "dump" : "Dump operations without compilation",
        "dump_proc" : "Dump operations of a specific procedure",
        "dump_tokens" : "Dump tokens without parsing or compilating",
        "dump_tc" : "Dump operations after type checking",
        "out" : "The name for output file(s)",
        "target" : "A taget to compile to",
        "config" : "Config file",
        "stdout" : "File to output stdout of complier and program",
        "input" : "Stdin for program",
        "error" : "Stderr for program",
    }

    BOOL_OPTIONS: Dict[str, Tuple[List[str], bool]] = {
        "run" : (["-r", "-run"], False),
        "dump" : (["-d", "-dump"], False),
        "dump_tokens" : (["-dt", "-dump_tokens"], False),
        "dump_tc" : (["-dtc", "-dump_tc"], False),
    }

    REGULAR_OPTIONS: Dict[str, List[str]] = {
        "out" : (["-o", "--out"], None),
        "target" : (["-t", "--target"], "fasm_x86_64_linux"),
        "dump_proc" : (["-dp", "--dump_proc"], None),
        "stdout" : (["-stdo", "--stdout"], None),
        "input" : (["-i", "--input"], None),
        "error" : (["-e", "--error"], None),
    }
    CONFIG_REGULAR_OPTIONS: List[str] = ["out", "target"]

    CONFIG_BOOL_OPTIONS: Dict[str, bool] = {
        "re_IOR" : True,
        "re_NPD" : True,
        "o_UPR" : True,
    }

    CONFIG_BOOL_CLEAR_OPTIONS: Dict[str, bool] = {
        "struct_malloc" : True,
    }

    CONFIG_INT_OPTIONS: Dict[str, int] = {
        "size_call_stack" : 65536,
        "size_bind_stack" : 8192,
    }

    CHECK_POSITIVE: List[str] = ["size_call_stack", "size_bind_stack"]

    def __init__(self, argv, lsp_mode: bool = False):
        self.lsp_mode = lsp_mode
        self.args = self.setup_args_parser().parse_args(argv[1:])
        self.config, config_file = self.load_config(self.args.config)
        self.define_properties()
        if config_file:
            self._validate(config_file)
        self._validate_target()

    def setup_args_parser(self) -> argparse.ArgumentParser:
        """Creates, configures and returns an `ArgumentParser`"""
        args_parser = argparse.ArgumentParser()

        args_parser.add_argument("program", help=self.DESCRIPTIONS["program"])
        args_parser.add_argument(
            "-c",
            "--config",
            default=None,
            dest="config",
            help=self.DESCRIPTIONS["config"],
        )

        for name, i in self.BOOL_OPTIONS.items():
            args_parser.add_argument(
                *i[0],
                action="store_true",
                default=i[1],
                dest=name,
                help=self.DESCRIPTIONS[name],
            )

        for name, args in self.REGULAR_OPTIONS.items():
            args_parser.add_argument(
                *args[0], default=None, dest=name, help=self.DESCRIPTIONS[name]
            )

        return args_parser

    def _validate_target(self):
        """Checks if the target is a valid one"""
        if self.target not in TARGETS:
            print(f"\033[1;31mError\033[0m: target not found: {self.target}")
            exit(1)

    @property
    def _valid_keys(self) -> Tuple[str, ...]:
        """Returns a tuple of all the valid option ids"""
        return (
            *self.CONFIG_REGULAR_OPTIONS, *self.CONFIG_BOOL_OPTIONS,
            *self.CONFIG_INT_OPTIONS, *self.CONFIG_BOOL_CLEAR_OPTIONS,
        )

    def load_config(self, config_file: Optional[str]) -> Tuple[Dict[str, Any], str]:
        """
        Loads a config at the path `config_file`.
        If the path is None loads from the default location if it is present.

        Returns a tuple of the deserialized json and the path to the config. 
        """
        if config_file is None:
            if "cont_build.json" in os.listdir():
                return self.load_config("cont_build.json")
            return ({}, "")

        with open(config_file, "r") as f:
            return (json.load(f), config_file)

    def define_properties(self):
        """Defines all the properties for the config options"""
        for name in self.BOOL_OPTIONS:
            setattr(
                self.__class__, name,
                property(fget=lambda self, name=name: getattr(self.args, name)),
            )

        for name in self.REGULAR_OPTIONS:
            setattr(
                self.__class__, name,
                property(
                    fget=lambda self, name=name: self.config.get(
                        name, getattr(self.args, name) 
                        if getattr(self.args, name) is not None 
                        else self.REGULAR_OPTIONS[name][1])
                )
            )

        for name, default in {**self.CONFIG_BOOL_OPTIONS, **self.CONFIG_INT_OPTIONS}.items():
            setattr(
                self.__class__, name,
                property(
                    fget=lambda self, name=name, default=default: self.config.get(
                        name, default
                    )
                ),
            )

        for name, default in self.CONFIG_BOOL_CLEAR_OPTIONS.items():
            setattr(
                self.__class__, name,
                property(
                    fget=lambda self, name=name, default=default: (
                        name in self.config,
                        self.config.get(name, default),
                    )
                ),
            )

    def _is_key_valid(self, key: str) -> bool:
        """Checks whether the option id in the config file is valid. Returns True if it is."""
        return key in self._valid_keys

    def _validate(self, config_file: str):
        """
        Validates the loaded config file.

        The path to the config file is used for the warnings and
        should be provided with the `config_file` argument.
        """
        for key in self.config.copy():
            if not self._is_key_valid(key):
                del self.config[key]
                if not self.lsp_mode:
                    print(
                        f"\033[1;33mWarning {config_file}\033[0m: config option {key} not found, ignoring"
                    )

        for field in self.CHECK_POSITIVE:
            if getattr(self, field) <= 0:
                if not self.lsp_mode:
                    print(
                        f"\033[1;33mWarning {config_file}\033[0m: invalid value for {field}, using default "
                        + str(self.CONFIG_INT_OPTIONS[field])
                    )
                del self.config[field]
                assert getattr(self, field) > 0, "Wrong default value for field"

    @property
    def program(self) -> str:
        """The program to be compiled"""
        return self.args.program
