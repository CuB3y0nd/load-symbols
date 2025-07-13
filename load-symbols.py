#!/usr/bin/env python3

import argparse
import os

import gdb

CRE = "\x1b[0;31m"
CGR = "\x1b[0;32m"
CYW = "\x1b[0;33m"
CPR = "\x1b[0;35m"
CAQ = "\x1b[0;36m"
CNC = "\x1b[0m"

# Supported file extensions
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
        gdb.write(f"{CGR}Loaded symbols from {CPR}'{path}'{CNC}\n")
        return 1
    except gdb.error as e:
        gdb.write(f"{CRE}{str(e).replace('`', "'")}{CNC}\n")
        return 0


def load_debug_symbols_recursive(path: str):
    """Recursively load all supported symbol files in the directory."""
    try:
        items = os.listdir(path)
    except Exception as e:
        gdb.write(f"""{CRE}Cannot list directory: {e}{CNC}
{CYW}No debug symbols are loaded.{CNC}
""")
        return None

    count = 0
    for item in items:
        full_path = os.path.join(path, item)
        if os.path.isfile(full_path) and full_path.endswith(SUPPORTED_EXTS):
            count += try_load_symbol(full_path)
        elif os.path.isdir(full_path):
            count += load_debug_symbols_recursive(full_path) or 0
    return count


class LoadSymbolsCommand(gdb.Command):
    def __init__(self):
        super().__init__("load-symbols", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            args = PARSER.parse_args(arg.split())
        except SystemExit:
            return

        path = os.path.abspath(args.path)

        # Single file case
        if os.path.isfile(path):
            if path.endswith(SUPPORTED_EXTS):
                count = try_load_symbol(path)
                gdb.write(f"{CAQ}Total loaded {CYW}{count} {CAQ}symbol file.{CNC}\n")
            else:
                gdb.write(f"{CYW}Unsupported file type: {CPR}'{path}'{CNC}\n")
            return

        # Invalid path
        if not os.path.isdir(path):
            gdb.write(
                f"""{CRE}load-symbols: path does not exist: {CPR}'{path}'{CNC}
{CYW}No debug symbols are loaded.{CNC}
"""
            )
            return

        # Directory case
        count = load_debug_symbols_recursive(path)

        if count is None:
            return
        if count == 0:
            gdb.write(f"{CYW}No symbol files were found in: {CPR}'{path}'{CNC}\n")
        else:
            gdb.write(f"{CAQ}Total loaded {CYW}{count} {CAQ}symbol files.{CNC}\n")


LoadSymbolsCommand()
