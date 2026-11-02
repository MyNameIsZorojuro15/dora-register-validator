"""Load a register (one CSV per template), run every rule, return the issues as one table."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import duckdb
import pandas as pd

from . import checks
from .model import TEMPLATES
from .reference import SPEND_TOLERANCE, ROOT
from .rules import BY_ID

SQL_DIR = ROOT / "sql"
ISSUE_COLUMNS = ["rule_id", "severity", "template", "row", "key", "column", "value", "message", "fix", "eba_ref", "basis"]


def table_name(code: str) -> str:
    return code.lower().replace(".", "_")


def read_register(folder: Path) -> Dict[str, pd.DataFrame]:
    """One CSV per template (B_01.01.csv ...). All values are read as text; blank stays ''.
    A missing file is read as an empty template (rule DRV-01)."""
    tables = {}
    for code, t in TEMPLATES.items():
        f = Path(folder) / f"{code}.csv"
        if f.exists():
            df = pd.read_csv(f, dtype=str, keep_default_na=False)
        else:
            df = pd.DataFrame(columns=t.codes)
        df = df.reindex(columns=t.codes, fill_value="")
        df["_row"] = range(2, len(df) + 2)   # CSV line number: header is line 1
        tables[code] = df
    return tables


def _sql_issues(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    con = duckdb.connect()
    for code, df in tables.items():
        con.register(table_name(code), df)
    frames = []
    for f in sorted(SQL_DIR.glob("[12]0_*.sql")):
        frames.append(con.execute(f.read_text(), {"tol": SPEND_TOLERANCE} if "$tol" in f.read_text() else None).df())
    con.close()
    out = pd.concat(frames, ignore_index=True)
    return out.rename(columns={"col": "column"})


def validate(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    py = pd.DataFrame(checks.run(tables))
    # cross-template SQL needs rows in the tables it joins; an empty template is already reported by DRV-01
    sql = _sql_issues(tables)
    df = pd.concat([py, sql], ignore_index=True) if len(py) else sql
    if df.empty:
        return pd.DataFrame(columns=ISSUE_COLUMNS)
    df["row"] = df["row"].astype(int)
    df["severity"] = df["rule_id"].map(lambda r: BY_ID[r].severity)
    df["fix"] = df["rule_id"].map(lambda r: BY_ID[r].fix)
    df["eba_ref"] = df["rule_id"].map(lambda r: BY_ID[r].eba_ref)
    df["basis"] = df["rule_id"].map(lambda r: BY_ID[r].basis)
    order = {"error": 0, "warning": 1}
    df["_s"] = df["severity"].map(order)
    df = df.sort_values(["_s", "template", "row", "rule_id"]).drop(columns="_s").reset_index(drop=True)
    return df[ISSUE_COLUMNS]


def validate_folder(folder: Path) -> pd.DataFrame:
    return validate(read_register(folder))
