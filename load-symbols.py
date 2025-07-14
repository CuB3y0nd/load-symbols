#!/usr/bin/env python3

import argparse
import os

import gdb

RED = "\x1b[0;31m"
GRE = "\x1b[0;32m"
YEL = "\x1b[0;33m"
PUR = "\x1b[0;35m"
AQU = "\x1b[0;36m"
RST = "\x1b[0m"

# supported file extensions
SUPPORTED_EXTS = (".debug", ".so", ".sym")

PARSER = argparse.ArgumentParser(
    prog="load-symbols",
    description="Recursively load all symbol files from a directory or load a single symbol file.",
)
PARSER.add_argument("path", help="Path to a symbol file or directory.")


def try_load_symbol(path: str):
    """Try loading a single symbol file. Returns 1 if successful, 0 otherwise."""
    try:
        gdb.execute(f"add-symbol-file {path}", to_string=True)
        gdb.write(f"{GRE}Loaded symbols from {PUR}'{path}'{RST}\n")
        return 1
    except gdb.error as e:
        gdb.write(f"{RED}{str(e).replace('`', "'")}{RST}\n")
        return 0


def load_symbols(path):
    """Iterate with os.walk"""
    loaded = 0

    try:
        for root, _, files in os.walk(path):
            for fname in files:
                if fname.endswith(SUPPORTED_EXTS):
                    full_path = os.path.join(root, fname)
                    loaded += try_load_symbol(full_path)
    except KeyboardInterrupt:
        gdb.write(
            f"{YEL}\nInterrupted by user. Loaded {AQU}{loaded}{YEL} files so far.{RST}\n"
        )
        return None
    return loaded


class LoadSymbolsCommand(gdb.Command):
    def __init__(self):
        super().__init__("load-symbols", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            args = PARSER.parse_args(arg.split())
        except SystemExit:
            return

        path = os.path.abspath(args.path)

        # single file case
        if os.path.isfile(path):
            if path.endswith(SUPPORTED_EXTS):
                count = try_load_symbol(path)
                gdb.write(f"{AQU}Total loaded {YEL}{count}{AQU} symbol file.{RST}\n")
            else:
                gdb.write(f"{YEL}Unsupported file type: {PUR}'{path}'{RST}\n")
            return

        # invalid path
        if not os.path.isdir(path):
            gdb.write(f"{RED}load-symbols: path does not exist: {PUR}'{path}'{RST}\n")
            return

        # directory case
        total = load_symbols(path)

        if total is None:
            return
        if total == 0:
            gdb.write(f"{YEL}No symbol files were found in: {PUR}'{path}'{RST}\n")
        else:
            gdb.write(f"{AQU}Total loaded {YEL}{total}{AQU} symbol files.{RST}\n")


LoadSymbolsCommand()
