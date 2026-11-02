"""Rules that look at one template at a time (pandas). Cross-template rules are in sql/."""
from __future__ import annotations

import re
from datetime import date
from typing import Dict, List

import pandas as pd

from . import lei as leimod
from .model import TEMPLATES, Template
from .reference import BOOL_VALUES, COUNTRIES, CURRENCIES, HARD_TO_SUBSTITUTE, TRUE_VALUES, VOCAB

EUID_FORMAT = re.compile(r"^[A-Z]{2}[A-Z0-9]{1,12}\.[A-Za-z0-9/\- ]{1,40}$")  # country + register id + '.' + number
INT_FORMAT = re.compile(r"^-?\d+$")
MONEY_FORMAT = re.compile(r"^-?\d+(\.\d+)?$")
DATE_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}$")

Issue = Dict[str, object]


def parse_date(s: str):
    """A real calendar date in yyyy-mm-dd, else None."""
    if not DATE_FORMAT.match(s or ""):
        return None
    try:
        return date(int(s[:4]), int(s[5:7]), int(s[8:]))
    except ValueError:
        return None


def _key(t: Template, r: pd.Series) -> str:
    return "|".join(str(r[c]) for c in t.pk)


def _add(out: List[Issue], rule: str, t: Template, r: pd.Series, col: str, msg: str) -> None:
    out.append({"rule_id": rule, "template": t.code, "row": int(r["_row"]), "key": _key(t, r), "column": col,
                "value": r[col] if col in r.index else "", "message": msg})


def reporting_date(tables: Dict[str, pd.DataFrame]):
    df = tables.get("B_01.01")
    if df is None or df.empty:
        return None
    return parse_date(df.iloc[0]["c0060"])


def run(tables: Dict[str, pd.DataFrame]) -> List[Issue]:
    out: List[Issue] = []
    ref_date = reporting_date(tables)
    for code, t in TEMPLATES.items():
        df = tables[code]
        if df.empty:                                                                          # DRV-01
            out.append({"rule_id": "DRV-01", "template": code, "row": 0, "key": "", "column": "", "value": "",
                        "message": f"{code} ({t.name}) has no rows"})
            continue
        for _, r in df.iterrows():
            for c in t.cols:
                v = r[c.code]
                label = f"{c.code} {c.label}"
                if v == "":
                    if c.required:                                                            # DRV-02
                        _add(out, "DRV-02", t, r, c.code, f"Mandatory field is blank: {label}")
                    continue
                kind = c.kind
                if kind == "lei":
                    _lei(out, t, r, c, v, label)
                elif kind == "pid":
                    _pid(out, t, r, c, v, label)
                elif kind == "country":
                    if v not in COUNTRIES:                                                    # DRV-06
                        _add(out, "DRV-06", t, r, c.code, f"'{v}' is not an ISO 3166-1 alpha-2 country code: {label}")
                elif kind == "currency":
                    if v not in CURRENCIES:                                                   # DRV-07
                        _add(out, "DRV-07", t, r, c.code, f"'{v}' is not an ISO 4217 currency code: {label}")
                elif kind in ("date", "dpast"):
                    d = parse_date(v)
                    if d is None:                                                             # DRV-10
                        _add(out, "DRV-10", t, r, c.code, f"'{v}' is not a valid yyyy-mm-dd date: {label}")
                    elif kind == "dpast" and ref_date and d > ref_date:                       # DRV-14
                        _add(out, "DRV-14", t, r, c.code, f"{v} is after the reporting date {ref_date}: {label}")
                elif kind == "int":
                    if not INT_FORMAT.match(v):                                               # DRV-11
                        _add(out, "DRV-11", t, r, c.code, f"'{v}' is not a whole number: {label}")
                elif kind == "money":
                    if not MONEY_FORMAT.match(v):                                             # DRV-11
                        _add(out, "DRV-11", t, r, c.code, f"'{v}' is not an amount: {label}")
                    elif float(v) < 0:                                                        # DRV-12
                        _add(out, "DRV-12", t, r, c.code, f"Negative amount {v}: {label}")
                elif kind == "bool":
                    if v not in BOOL_VALUES:                                                  # DRV-09
                        _add(out, "DRV-09", t, r, c.code, f"'{v}' is not true/false/1/0: {label}")
                elif kind == "ptype" or kind.startswith("enum:"):
                    name = "code_type" if kind == "ptype" else kind.split(":", 1)[1]
                    if v not in VOCAB[name]:                                                  # DRV-09
                        _add(out, "DRV-09", t, r, c.code, f"'{v}' is not an allowed value: {label}")
        _conditional(out, t, df)
    return out


def _lei(out, t, r, c, v, label) -> None:
    if not leimod.has_valid_format(v):                                                        # DRV-04
        _add(out, "DRV-04", t, r, c.code, f"'{v}' is not 18 upper-case letters/digits + 2 digits: {label}")
    elif not leimod.has_valid_checksum(v):                                                    # DRV-05
        _add(out, "DRV-05", t, r, c.code, f"'{v}' fails the ISO 17442 check digits: {label}")


def _pid(out, t, r, c, v, label) -> None:
    declared = r[c.type_col] if c.type_col else ""
    if declared == "EUID":
        if not EUID_FORMAT.match(v):                                                          # DRV-08
            _add(out, "DRV-08", t, r, c.code, f"'{v}' is declared EUID but is not shaped like one: {label}")
    elif declared == "LEI":
        if "." in v:                                                                          # DRV-08
            _add(out, "DRV-08", t, r, c.code, f"'{v}' is declared LEI but looks like an EUID: {label}")
        else:
            _lei(out, t, r, c, v, label)
    elif declared == "" and "." not in v:
        _lei(out, t, r, c, v, label)  # no declared type: a code without a dot is read as an LEI


def _true(v: str) -> bool:
    return v in TRUE_VALUES


def _conditional(out, t: Template, df: pd.DataFrame) -> None:
    code = t.code
    for _, r in df.iterrows():
        if code == "B_01.02":
            if r["c0110"] != "" and r["c0100"] == "":                                         # DRV-17
                _add(out, "DRV-17", t, r, "c0100", "Total assets reported without a currency")
            u, i, d = parse_date(r["c0070"]), parse_date(r["c0080"]), parse_date(r["c0090"])
            if u and i and u < i:                                                             # DRV-15
                _add(out, "DRV-15", t, r, "c0070", f"Last update {r['c0070']} is before integration {r['c0080']}")
            if d and i and d < i:                                                             # DRV-15
                _add(out, "DRV-15", t, r, "c0090", f"Deletion {r['c0090']} is before integration {r['c0080']}")
        elif code == "B_05.01":
            if r["c0100"] != "" and r["c0090"] == "":                                         # DRV-17
                _add(out, "DRV-17", t, r, "c0090", "Total expense reported without a currency")
        elif code == "B_02.01":
            if r["c0020"] == "Subsequent or associated arrangement" and r["c0030"] == "":     # DRV-18
                _add(out, "DRV-18", t, r, "c0030", "Subsequent arrangement without an overarching reference")
        elif code == "B_02.02":
            s, e = parse_date(r["c0070"]), parse_date(r["c0080"])
            if s and e and e <= s:                                                            # DRV-13
                _add(out, "DRV-13", t, r, "c0080", f"End date {r['c0080']} is not after start date {r['c0070']}")
            if r["c0090"] != "" and r["c0080"] == "":                                         # DRV-16
                _add(out, "DRV-16", t, r, "c0090", "Termination reason given but no end date")
            if _true(r["c0140"]) and r["c0150"] == "":                                        # DRV-23
                _add(out, "DRV-23", t, r, "c0150", "Data is stored but the storage location is blank")
        elif code == "B_04.01":
            if r["c0030"] in BOOL_VALUES and _true(r["c0030"]) != (r["c0040"] != ""):         # DRV-19
                _add(out, "DRV-19", t, r, "c0040", "Branch flag and branch code disagree")
        elif code == "B_06.01":
            if r["c0050"] == "Yes" and r["c0060"] == "":                                      # DRV-21
                _add(out, "DRV-21", t, r, "c0060", "Critical or important function without reasons")
        elif code == "B_07.01":
            if r["c0050"] in HARD_TO_SUBSTITUTE and r["c0060"] == "":                         # DRV-20
                _add(out, "DRV-20", t, r, "c0060", f"'{r['c0050']}' needs a reason")
            if _true(r["c0110"]) and r["c0120"] == "":                                        # DRV-22
                _add(out, "DRV-22", t, r, "c0120", "Alternatives flagged but not identified")
    dup = df.duplicated(subset=t.pk, keep=False)                                              # DRV-03
    for _, r in df[dup].iterrows():
        _add(out, "DRV-03", t, r, t.pk[0], "Duplicate key")
