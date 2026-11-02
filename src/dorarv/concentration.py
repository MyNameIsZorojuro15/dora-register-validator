"""Concentration view: spend and criticality by provider group and by country, plus risk flags (DORA Art. 29)."""
from __future__ import annotations

from typing import Dict

import duckdb
import pandas as pd

from .reference import EU_MEMBERS, HARD_TO_SUBSTITUTE, THRESHOLDS, load_fx
from .rules import BY_ID
from .validate import SQL_DIR, table_name


def _con(tables: Dict[str, pd.DataFrame]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for code, df in tables.items():
        con.register(table_name(code), df)
    con.register("fx_rates", pd.DataFrame(sorted(load_fx().items()), columns=["currency", "eur_per_unit"]))
    con.register("hard", pd.DataFrame({"label": list(HARD_TO_SUBSTITUTE)}))
    con.register("eu_members", pd.DataFrame({"code": sorted(EU_MEMBERS)}))
    return con


def views(tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    con = _con(tables)
    out = {name: con.execute((SQL_DIR / f).read_text()).df() for name, f in [
        ("groups", "30_concentration_by_group.sql"), ("countries", "31_concentration_by_country.sql"),
        ("functions", "32_critical_function_dependency.sql")]}
    con.close()
    return out


def flags(v: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    g, c, f = v["groups"], v["countries"], v["functions"]
    for r in g.itertuples():
        if r.spend_share >= THRESHOLDS["provider_spend_share"]:
            rows.append(("CON-01", r.group_name, f"{r.spend_share:.1%} of ICT spend", f">= {THRESHOLDS['provider_spend_share']:.0%}"))
        if r.critical_functions >= THRESHOLDS["critical_functions_supported"]:
            rows.append(("CON-02", r.group_name, f"{r.critical_functions} critical functions", f">= {THRESHOLDS['critical_functions_supported']}"))
    for r in c[(c["basis"] == "ultimate parent headquarters") & (~c["in_eu"])].itertuples():
        if r.spend_share >= THRESHOLDS["third_country_spend_share"]:
            rows.append(("CON-03", r.country, f"{r.spend_share:.1%} of ICT spend", f">= {THRESHOLDS['third_country_spend_share']:.0%}"))
    for r in f[f["single_provider"]].itertuples():
        rows.append(("CON-04", f"{r.function_id} {r.function_name}", "1 provider", "> 1"))
    df = pd.DataFrame(rows, columns=["flag_id", "subject", "value", "threshold"])
    df["description"] = df["flag_id"].map(lambda i: BY_ID[i].name)
    df["suggested_action"] = df["flag_id"].map(lambda i: BY_ID[i].fix)
    return df
