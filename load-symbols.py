#!/usr/bin/env python3

import gdb
import os


CRE = "\x1b[0;31m"
CGR = "\x1b[0;32m"
CYW = "\x1b[0;33m"
CPR = "\x1b[0;35m"
CNC = "\x1b[0m"


def load_debug_symbols(path):
    try:
        items = os.listdir(path)
    except Exception as e:
        gdb.write(f"{CRE}Cannot list directory: {e}{CNC}\n")
        return

    for item in items:
        item_path = os.path.join(path, item)

        if os.path.isfile(item_path) and item_path.endswith((".debug", ".so", ".sym")):
            try:
                gdb.execute(f"add-symbol-file {item_path}", to_string=True)
                gdb.write(f"{CGR}Loaded symbols from {CPR}'{item_path}'{CNC}\n")
            except gdb.error as e:
                gdb.write(f"{CRE}{str(e).replace('`', "'")}{CNC}\n")
        elif os.path.isdir(item_path):
            load_debug_symbols(item_path)


class LoadSymbolsCommand(gdb.Command):
    def __init__(self):
        super().__init__("load-symbols", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        arg = arg.strip()

        if arg in ("-h", "--help") or not arg:
            gdb.write("""usage: load-symbols [-h] [path]

Recursively load all symbol files from a directory and its subdirectories.

positional arguments:
  path        The folder path of debug symbols you want to load.

options:
  -h, --help  show this help message and exit
""")
            return

        path = os.path.abspath(arg)

        if not os.path.exists(path) or not os.path.isdir(path):
            gdb.write(
                f"""{CRE}load-symbols: path does not exist: {CPR}'{path}'
{CYW}No debug symbols is loaded.{CNC}
"""
            )
            return

        load_debug_symbols(path)


LoadSymbolsCommand()
