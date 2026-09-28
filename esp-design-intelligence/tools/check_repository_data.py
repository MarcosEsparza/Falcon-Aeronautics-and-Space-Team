"""Reject common data-export formats before local commits and in pull requests.

An extension filter prevents common accidents. It cannot classify file contents,
inspect encrypted archives, or replace an organization's data-handling policy.
"""

import argparse
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BLOCKED_SUFFIXES = frozenset({
    ".xlsx", ".xls", ".xlsm", ".xlsb", ".csv", ".tsv",
    ".parquet", ".feather", ".sqlite", ".sqlite3", ".db", ".duckdb",
    ".mdb", ".accdb", ".pkl", ".pickle", ".jsonl",
    ".zip", ".7z", ".rar", ".tar", ".gz",
})


def blocked_paths(paths):
    """Return distinct prohibited paths without inspecting their contents."""
    return sorted({
        path for path in paths
        if PurePosixPath(path.replace("\\", "/")).suffix.lower() in BLOCKED_SUFFIXES
    })


def git_paths(*args):
    result = subprocess.run(
        ["git", *args], cwd=REPOSITORY_ROOT, check=True, capture_output=True
    )
    return [os.fsdecode(item) for item in result.stdout.split(b"\0") if item]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--staged", action="store_true", help="Check locally staged files")
    choice.add_argument(
        "--compare", nargs=2, metavar=("BASE_SHA", "HEAD_SHA"),
        help="Check files introduced or modified between two commits",
    )
    args = parser.parse_args(argv)

    try:
        if args.staged:
            paths = git_paths("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
        else:
            paths = git_paths(
                "diff", "--name-only", "--diff-filter=ACMR",
                "-z", args.compare[0], args.compare[1],
            )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Data-file guard could not inspect Git; commit/check blocked.", file=sys.stderr)
        return 2

    rejected = blocked_paths(paths)
    if rejected:
        print(
            f"Blocked {len(rejected)} potential data file(s). Paths are withheld from logs. "
            "Inspect staged/changed files locally and remove confidential data from Git.",
            file=sys.stderr,
        )
        return 1
    print("Data-file guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
