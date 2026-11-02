"""Validate any folder that holds one CSV per template: python -m dorarv.cli <folder> [--out issues.csv]"""
from __future__ import annotations

import argparse
from pathlib import Path

from .validate import validate_folder


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate a DORA register of information (one CSV per template, EBA column codes).")
    ap.add_argument("folder", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="write the issues report to this CSV")
    a = ap.parse_args(argv)
    issues = validate_folder(a.folder)
    n_err = int((issues["severity"] == "error").sum())
    print(f"{len(issues)} issues ({n_err} errors, {len(issues) - n_err} warnings)")
    if a.out:
        issues.to_csv(a.out, index=False)
        print(f"written to {a.out}")
    return 1 if n_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
