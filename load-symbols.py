#!/usr/bin/env python3

import argparse
import os
import re
import shlex

import gdb


class Color:
    RED = "\x1b[0;31m"
    GRE = "\x1b[0;32m"
    BLU = "\x1b[0;34m"
    YEL = "\x1b[0;33m"
    PUR = "\x1b[0;35m"
    AQU = "\x1b[0;36m"
    RST = "\x1b[0m"


class log:
    @staticmethod
    def info(msg):
        gdb.write(f"{Color.BLU}{msg}{Color.RST}\n")

    @staticmethod
    def warn(msg):
        gdb.write(f"{Color.YEL}{msg}{Color.RST}\n")

    @staticmethod
    def error(msg):
        gdb.write(f"{Color.RED}{msg}{Color.RST}\n")

    @staticmethod
    def success(msg):
        gdb.write(f"{Color.GRE}{msg}{Color.RST}\n")


# default supported file extensions
DEFAULT_EXTS: set[str] = {".debug", ".so", ".sym"}

# avoid duplicates
_loaded: set[str] = set()

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

_PERM_RE = re.compile(r"(?P<path>/[^:]+): (?P<reason>Permission denied*)")


def parse_extensions(s: str) -> tuple[str, ...]:
    """
    Combine default extensions with user‑supplied ones.
    Ensures each ext starts with '.' and removes duplicates.
    """
    exts = set(DEFAULT_EXTS)
    for ext in map(str.strip, s.split(",")):
        if ext:
            exts.add(ext if ext.startswith(".") else "." + ext)
    return tuple(exts)


def try_load(path: str) -> tuple[bool, str | None]:
    """Load a single symbol file."""
    abs_path = os.path.realpath(path)

    if abs_path in _loaded:
        return False, "Already loaded"

    try:
        gdb.execute(f"add-symbol-file {path}", to_string=True)
        log.success(f"Loaded {Color.PUR}'{path}'")
        _loaded.add(abs_path)
        return True, None
    except gdb.error as e:
        msg = str(e).replace("`", "'")
        m = _PERM_RE.match(msg)
        if m:
            msg = f"{m.group('reason')}: '{m.group('path')}'"
        return False, msg


def load_dir(
    dir: str, exts: tuple[str, ...]
) -> tuple[int, int, list[str], list[tuple[str, str]]]:
    """
    Walk the directory tree and load all matching files.
    Returns the number of successfully‑loaded files.
    """
    loaded, skipped = 0, 0
    denied, unsupported, failed = [], [], []

    def on_err(e):
        if isinstance(e, PermissionError):
            denied.append(e.filename)

    for root, _, files in os.walk(dir, onerror=on_err):
        for f in files:
            full_path = os.path.join(root, f)
            if f.endswith(exts):
                if os.path.abspath(full_path) in _loaded:
                    skipped += 1
                else:
                    ok, reason = try_load(full_path)
                    if ok:
                        loaded += 1
                    else:
                        failed.append((full_path, reason or "Unknown error"))
            else:
                unsupported.append(full_path)

    for path in denied:
        log.error(f"Permission denied: '{path}'")

    return loaded, skipped, unsupported, failed


def _report_failures(failed: list[tuple[str, str]]):
    if not failed:
        return
    log.error(f"Failed to load {Color.AQU}{len(failed)}{Color.RED} file(s):")
    for _path, reason in failed[:5]:
        log.error(f"  {reason}{Color.RST}\n")
    if len(failed) > 5:
        log.error(f"  ... and {len(failed) - 5} more.")


def _report_unsupported(unsupported: list[str]):
    if not unsupported:
        return
    log.warn(
        f"Skipped {Color.AQU}{len(unsupported)}{Color.YEL} unsupported file(s) (judge by extension):"
    )
    for path in unsupported[:5]:
        log.info(f"{Color.PUR}  '{path}'{Color.RST}")
    if len(unsupported) > 5:
        log.warn(f"  ... and {Color.AQU}{len(unsupported) - 5}{Color.YEL} more.")


class LoadSymbolsCommand(gdb.Command):
    def __init__(self):
        super().__init__("load-symbols", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            args = PARSER.parse_args(shlex.split(arg))
        except SystemExit:
            return

        path = os.path.abspath(args.path)
        exts = parse_extensions(args.ext)

        # single file
        if os.path.isfile(path):
            if path.endswith(exts):
                success, reason = try_load(path)
                if success:
                    log.info(f"Total loaded {Color.AQU}1  symbol file.")
                else:
                    log.error(f"{reason}")
            else:
                log.warn(f"Unsupported file (judge by extension): {Color.PUR}'{path}'")
            return

        # not a dir
        if not os.path.isdir(path):
            log.error(f"load-symbols: no such path: {Color.PUR}'{path}'{Color.RST}")
            return

        # dir but no access at all
        if not os.access(path, os.R_OK | os.X_OK):
            log.error(f"Permission denied: '{path}'")
            return

        total, skipped, unsupported, failed = load_dir(path, exts)
        if total == 0:
            if skipped > 0:
                log.info(
                    f"All loadable symbol files in {Color.PUR}'{path}' {Color.BLU}have already been loaded.\n"
                )
            else:
                log.warn(f"No symbol files were loaded from: {Color.PUR}'{path}'")
        else:
            log.info(f"\nTotal loaded {Color.AQU}{total}{Color.BLU} symbol files.\n")

        _report_failures(failed)
        _report_unsupported(unsupported)


LoadSymbolsCommand()
