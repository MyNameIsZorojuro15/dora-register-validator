import re

import duckdb
import pandas as pd

from dorarv import validate as V
from dorarv.model import TEMPLATES
from dorarv.reference import SPEND_TOLERANCE
from dorarv.rules import BY_ID


def _files():
    return sorted(V.SQL_DIR.glob("*.sql"))


def test_sql_files_exist():
    names = {f.name for f in _files()}
    assert {"10_referential.sql", "20_consistency.sql", "30_concentration_by_group.sql"} <= names


def test_sql_rule_ids_are_in_the_catalogue():
    used = set()
    for f in V.SQL_DIR.glob("[12]0_*.sql"):
        used |= set(re.findall(r"'(DRV-\d+)'", f.read_text()))
    assert used and used <= set(BY_ID)
    assert {"DRV-30", "DRV-31", "DRV-32", "DRV-33", "DRV-34", "DRV-35", "DRV-36", "DRV-40", "DRV-41", "DRV-42", "DRV-43",
            "DRV-44", "DRV-45", "DRV-46", "DRV-47"} <= used


def test_sql_output_columns(clean):
    con = duckdb.connect()
    for code, df in clean.items():
        con.register(V.table_name(code), df)
    for f in V.SQL_DIR.glob("[12]0_*.sql"):
        txt = f.read_text()
        out = con.execute(txt, {"tol": SPEND_TOLERANCE} if "$tol" in txt else None).df()
        assert {"rule_id", "template", "row", "key", "col", "value", "message"} <= set(out.columns), f.name
        assert out.empty


def test_empty_tables_do_not_crash(clean):
    empty = {k: v.iloc[0:0].copy() for k, v in clean.items()}
    issues = V.validate(empty)
    assert set(issues[issues["rule_id"] == "DRV-01"]["template"]) == set(TEMPLATES)
    assert issues["rule_id"].isin(BY_ID).all()


def test_table_name():
    assert V.table_name("B_02.01") == "b_02_01"


def test_read_register_adds_row_numbers_starting_at_two(clean):
    for df in clean.values():
        assert df["_row"].iloc[0] == 2 and df["_row"].is_monotonic_increasing
    assert all(df.drop(columns="_row").map(lambda x: isinstance(x, str)).all().all() for df in clean.values())
