import pandas as pd
import pytest

from dorarv import concentration
from dorarv.reference import EU_MEMBERS, THRESHOLDS, load_fx


@pytest.fixture(scope="module")
def view(clean):
    return concentration.views(clean)


@pytest.fixture(scope="module")
def flg(view):
    return concentration.flags(view)


def test_group_shares_sum_to_one(view):
    assert view["groups"]["spend_share"].sum() == pytest.approx(1.0, abs=0.005)
    assert view["groups"]["spend_share"].is_monotonic_decreasing


def test_total_spend_matches_an_independent_computation(clean, view):
    k = clean["B_02.01"]
    k = k[k["c0020"] != "Overarching/master agreement"]
    fx = load_fx()
    total = sum(float(a) * fx[c] for a, c in zip(k["c0050"], k["c0040"]))
    assert view["groups"]["spend_eur"].sum() == pytest.approx(total, abs=len(view["groups"]))
    assert view["groups"]["contracts"].sum() == len(k)


def test_country_shares_sum_to_one_per_basis(view):
    for basis, x in view["countries"].groupby("basis"):
        assert x["spend_share"].sum() == pytest.approx(1.0, abs=0.01), basis


def test_critical_function_counts(clean, view):
    crit = clean["B_06.01"]
    assert len(view["functions"]) == (crit["c0050"] == "Yes").sum()
    assert set(view["functions"]["function_id"]) == set(crit[crit["c0050"] == "Yes"]["c0010"])
    assert view["groups"]["critical_functions"].max() <= len(view["functions"])


def test_flags_match_the_thresholds(view, flg):
    g = view["groups"]
    assert set(flg[flg.flag_id == "CON-01"]["subject"]) == set(g[g.spend_share >= THRESHOLDS["provider_spend_share"]]["group_name"])
    assert set(flg[flg.flag_id == "CON-02"]["subject"]) == set(
        g[g.critical_functions >= THRESHOLDS["critical_functions_supported"]]["group_name"])
    f = view["functions"]
    assert (flg.flag_id == "CON-04").sum() == int(f["single_provider"].sum())
    c = view["countries"]
    c = c[(c.basis == "ultimate parent headquarters") & ~c.in_eu & (c.spend_share >= THRESHOLDS["third_country_spend_share"])]
    assert set(flg[flg.flag_id == "CON-03"]["subject"]) == set(c["country"])


def test_eu_flag_is_consistent_with_the_member_list(view):
    c = view["countries"]
    assert all(r.in_eu == (r.country in EU_MEMBERS) for r in c.itertuples())


def test_concentration_changes_when_spend_moves(clean):
    t = {k: v.copy() for k, v in clean.items()}
    k = t["B_02.01"]
    i = k.index[k["c0020"] != "Overarching/master agreement"][0]
    k.at[i, "c0050"] = str(float(k.at[i, "c0050"]) + 50_000_000)
    v = concentration.views(t)
    assert v["groups"]["spend_share"].iloc[0] > 0.5
    assert (concentration.flags(v).flag_id == "CON-01").any()
