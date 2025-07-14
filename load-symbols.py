#!/usr/bin/env python3

import argparse
import os

import gdb


class Color:
    RED = "\x1b[0;31m"
    GRE = "\x1b[0;32m"
    YEL = "\x1b[0;33m"
    PUR = "\x1b[0;35m"
    AQU = "\x1b[0;36m"
    RST = "\x1b[0m"


# default supported file extensions
DEFAULT_EXTS: set[str] = {".debug", ".so", ".sym"}

_loaded: set[str] = set()  # avoid duplicates

PARSER = argparse.ArgumentParser(
    prog="load-symbols",
    description="Recursively load all symbol files from a directory or load a single symbol file.",
)
PARSER.add_argument("path", help="Path to a symbol file or directory.")
PARSER.add_argument(
    "--ext",
    help="Extra extensions, comma‑separated (e.g. --ext=.dbg,.elf)",
    default="",
)


def parse_extensions(s: str) -> tuple[str, ...]:
    """
    Combine default extensions with user‑supplied ones.
    Ensures each ext starts with '.' and removes duplicates.
    """
    exts = set(DEFAULT_EXTS)
    for ext in (e.strip() for e in s.split(",")):
        if ext:
            exts.add(ext if ext.startswith(".") else "." + ext)
    return tuple(exts)


def try_load(path: str) -> int:
    """Load a single symbol file."""
    real_path = os.path.abspath(path)

    if real_path in _loaded:
        return 0

    try:
        gdb.execute(f"add-symbol-file {path}", to_string=True)
        gdb.write(f"{Color.GRE}Loaded {Color.PUR}{path}{Color.RST}\n")
        _loaded.add(real_path)
        return 1
    except gdb.error as e:
        gdb.write(f"{Color.RED}{e}{Color.RST}\n")
        return 0


def load_dir(dir: str, exts: tuple[str, ...]) -> int:
    """
    Walk the directory tree and load all matching files.
    Returns the number of successfully‑loaded files.
    """
    loaded, denied = 0, []

    def on_err(err):
        if isinstance(err, PermissionError):
            denied.append(err.filename)

    try:
        for root, _, files in os.walk(dir, onerror=on_err):
            for f in files:
                if f.endswith(exts):
                    loaded += try_load(os.path.join(root, f))
    except KeyboardInterrupt:
        return loaded

    if denied:
        for d in denied:
            gdb.write(f"{Color.RED}Permission denied: {d}{Color.RST}\n")
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
        exts = parse_extensions(args.ext)

        # single file
        if os.path.isfile(path):
            if path.endswith(exts):
                total = try_load(path)
                gdb.write(
                    f"{Color.YEL}Total loaded {Color.AQU}{total}"
                    f"{Color.YEL} symbol file.{Color.RST}\n"
                )
            else:
                gdb.write(
                    f"{Color.YEL}Unsupported file: {Color.PUR}{path}{Color.RST}\n"
                )
            return

        # not a dir
        if not os.path.isdir(path):
            gdb.write(
                f"{Color.RED}load-symbols: no such path: {Color.PUR}{path}{Color.RST}\n"
            )
            return

        # dir but no access at all
        if not os.access(path, os.R_OK | os.X_OK):
            gdb.write(f"{Color.RED}Permission denied: {path}{Color.RST}\n")
            return

        total = load_dir(path, exts)
        if total == 0:
            gdb.write(
                f"{Color.YEL}No symbol files were loaded from: "
                f"{Color.PUR}{path}{Color.RST}\n"
            )
        else:
            gdb.write(
                f"\n{Color.YEL}Total loaded {Color.AQU}{total}"
                f"{Color.YEL} symbol files.{Color.RST}\n"
            )


LoadSymbolsCommand()
