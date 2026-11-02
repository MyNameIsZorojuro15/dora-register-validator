import copy
import json

import pandas as pd
import pytest

from dorarv.reference import ROOT
from dorarv.validate import read_register, validate

CLEAN = ROOT / "data" / "synthetic" / "clean"
DEFECTIVE = ROOT / "data" / "synthetic" / "defective"
REPORTS = ROOT / "reports"


@pytest.fixture(scope="session")
def clean():
    return read_register(CLEAN)


@pytest.fixture(scope="session")
def defective():
    return read_register(DEFECTIVE)


@pytest.fixture(scope="session")
def key():
    return pd.read_csv(DEFECTIVE / "answer_key.csv", dtype={"detectable": bool})


@pytest.fixture(scope="session")
def issues_clean(clean):
    return validate(clean)


@pytest.fixture(scope="session")
def issues_defective(defective):
    return validate(defective)


@pytest.fixture(scope="session")
def results():
    return json.loads((REPORTS / "results.json").read_text())


def mutated(tables, edits):
    """A copy of the register with single-cell edits [(template, row index, column, value)]."""
    t = {k: v.copy() for k, v in tables.items()}
    for code, i, col, val in edits:
        t[code].at[i, col] = val(tables) if callable(val) else val
    return t


def hits(issues):
    return {(r.rule_id, r.template, r.row - 2) for r in issues.itertuples()}
