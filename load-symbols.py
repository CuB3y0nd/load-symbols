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


PARSER = argparse.ArgumentParser(
    prog="load-symbols",
    description="Recursively load all symbol files from a directory and its subdirectories.",
)
PARSER.add_argument("path", help="Path to the directory containing symbol files.")


def load_debug_symbols(path):
    loaded_cnt = 0

    try:
        items = os.listdir(path)
    except Exception as e:
        gdb.write(
            f"""{CRE}Cannot list directory: {e}{CNC}
{CYW}No debug symbols are loaded.{CNC}
"""
        )
        return None

    for item in items:
        item_path = os.path.join(path, item)

        if os.path.isfile(item_path) and item_path.endswith((".debug", ".so", ".sym")):
            try:
                gdb.execute(f"add-symbol-file {item_path}", to_string=True)
                gdb.write(f"{CGR}Loaded symbols from {CPR}'{item_path}'{CNC}\n")

                loaded_cnt += 1
            except gdb.error as e:
                gdb.write(f"{CRE}{str(e).replace('`', "'")}{CNC}\n")
        elif os.path.isdir(item_path):
            loaded_cnt += load_debug_symbols(item_path) or 0
    return loaded_cnt


class LoadSymbolsCommand(gdb.Command):
    def __init__(self):
        super().__init__("load-symbols", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            args = PARSER.parse_args(arg.split())
        except SystemExit:
            return

        path = os.path.abspath(args.path)

        if os.path.isfile(path) and path.endswith((".debug", ".so", ".sym")):
            loaded_cnt = 0

            try:
                gdb.execute(f"add-symbol-file {path}", to_string=True)
                gdb.write(f"{CGR}Loaded symbols from {CPR}'{path}'{CNC}\n")

                loaded_cnt = 1
            except gdb.error as e:
                gdb.write(f"{CRE}{str(e).replace('`', "'")}{CNC}\n")
            gdb.write(f"{CAQ}Total loaded {CYW}{loaded_cnt} {CAQ}symbol file.{CNC}\n")
            return

        if not os.path.isdir(path):
            gdb.write(
                f"""{CRE}load-symbols: path does not exist: {CPR}'{path}'
{CYW}No debug symbols are loaded.{CNC}
"""
            )
            return

        loaded_cnt = load_debug_symbols(path)

        if loaded_cnt is None:
            return
        elif loaded_cnt == 0:
            gdb.write(f"{CYW}No symbol files were found in: {CPR}'{path}'{CNC}\n")
        else:
            gdb.write(f"{CAQ}Total loaded {CYW}{loaded_cnt} {CAQ}symbol files.{CNC}\n")


LoadSymbolsCommand()
