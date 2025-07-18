#!/usr/bin/env python3

import argparse
import os
import re
import shlex

import gdb


# built-in extensions whitelist
DEFAULT_EXTS: set[str] = {".debug", ".so", ".sym"}

# avoid duplicates
_loaded: set[str] = set()

# gdb's error string for a permission failure looks like:
#   "/path/to/file.debug: Permission denied"
_PERM_RE = re.compile(r"(?P<path>/[^:]+): (?P<reason>Permission denied*)")

# setup command info
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


class Color:
    RED = "\x1b[0;31m"
    GRE = "\x1b[0;32m"
    BLU = "\x1b[0;34m"
    YEL = "\x1b[0;33m"
    PUR = "\x1b[0;35m"
    CYA = "\x1b[0;36m"
    RST = "\x1b[0m"


class Logger:
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


def parse_extensions(s: str) -> tuple[str, ...]:
    """
    Combine DEFAULT_EXTS with a user‑supplied comma list.
    Ensures every entry starts with '.' and removes duplicates.
    """

    exts = set(DEFAULT_EXTS)
    for ext in map(str.strip, s.split(",")):
        if ext:
            exts.add(ext if ext.startswith(".") else "." + ext)
    return tuple(ext.lower() for ext in exts)


def try_load(path: str) -> tuple[bool, str | None]:
    """
    Attempt 'add-symbol-file <path>'.
    Returns (success, error_message).
    On success the file's realpath is recorded in _loaded.
    """

    abs_path = os.path.realpath(path)

    if abs_path in _loaded:
        return False, f"Already loaded: '{abs_path}'"

    try:
        gdb.execute(f"add-symbol-file {path}", to_string=True)
        Logger.success(f"Loaded {Color.PUR}'{path}'")
        _loaded.add(abs_path)
        return True, None
    except gdb.error as e:
        # normalise GDB error string and prettify permission error
        msg = str(e).replace("`", "'")
        m = _PERM_RE.match(msg)
        if m:
            msg = f"{m.group('reason')}: '{m.group('path')}'"
        else:
            msg = f"{msg}"


def load_dir(
    dir: str, exts: tuple[str, ...]
) -> tuple[int, int, list[str], list[tuple[str, str]]]:
    """
    Walk *directory* iteratively, call try_load() on every file
    whose name ends with one of *exts*.

    Returns:
        loaded         – number of files successfully loaded
        skipped        – number of already‑loaded files skipped
        unsupported    – paths filtered out by extension
        failed         – list[(path, reason)] of add‑symbol‑file failures
    """

    loaded = skipped = 0
    denied: list[str] = []
    unsupported: list[str] = []
    failed: list[tuple[str, str]] = []

    def on_err(exc: OSError):
        if isinstance(exc, PermissionError):
            denied.append(exc.filename)

    for root, _dirs, files in os.walk(dir, onerror=on_err):
        for fname in files:
            full_path = os.path.join(root, fname)
            if fname.endswith(tuple(exts)):
                if os.path.realpath(full_path) in _loaded:
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
        Logger.error(f"Permission denied: '{path}'\n")

    return loaded, skipped, unsupported, failed


def report_failures(failed: list[tuple[str, str]]) -> None:
    """Pretty‑print up to 5 failures."""

    if not failed:
        return

    Logger.error(f"\nFailed to load {Color.CYA}{len(failed)}{Color.RED} file(s):")
    for _path, reason in failed[:5]:
        Logger.error(f"  {reason}")
    Logger.error("")
    if len(failed) > 5:
        Logger.error(f"  ... and {Color.CYA}{len(failed) - 5}{Color.RED} more.")


def report_unsupportedr(unsupported: list[str]) -> None:
    """Print a short summary of files ignored due to extension filter."""

    if not unsupported:
        return

    Logger.warn(
        f"Skipped {Color.CYA}{len(unsupported)}{Color.YEL} unsupported file(s) (filtered by extension):"
    )
    for path in unsupported[:5]:
        Logger.warn(f"  {Color.PUR}'{path}'")
    if len(unsupported) > 5:
        Logger.warn(f"  ... and {Color.CYA}{len(unsupported) - 5}{Color.YEL} more.")


class LoadSymbolsCommand(gdb.Command):
    """Register `load-symbols` as a custom GDB command."""

    def __init__(self):
        super().__init__("load-symbols", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            args = PARSER.parse_args(shlex.split(arg))
        except SystemExit:
            PARSER.print_help()

        path = os.path.abspath(args.path)
        exts = parse_extensions(args.ext)

        # single file
        if os.path.isfile(path):
            if path.endswith(exts):
                success, reason = try_load(path)
                if success:
                    Logger.info(f"\nTotal loaded {Color.CYA}1{Color.BLU} symbol file.")
                else:
                    Logger.error(f"{reason}")
            else:
                Logger.warn(f"Unsupported file extension: {Color.PUR}'{path}'")
            return

        # not a dir
        if not os.path.isdir(path):
            Logger.error(
                f"Path is not a directory or does not exist: {Color.PUR}'{path}'"
            )
            return

        # dir but no access at all
        if not os.access(path, os.R_OK | os.X_OK):
            Logger.error(f"Permission denied: '{path}'")
            return

        total, skipped, unsupported, failed = load_dir(path, exts)

        if total:
            Logger.info(f"Total loaded {Color.CYA}{total}{Color.BLU} symbol files.")
        elif skipped:
            Logger.info(
                f"All loadable symbol files in {Color.PUR}'{path}'{Color.BLU} have already been loaded."
            )
        else:
            Logger.warn(f"No symbol files were loaded from: {Color.PUR}'{path}'")

        report_failures(failed)
        report_unsupportedr(unsupported)


# register with the current GDB session
LoadSymbolsCommand()
