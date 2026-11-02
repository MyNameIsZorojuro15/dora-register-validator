import pandas as pd

from dorarv import evaluate


def test_clean_register_raises_nothing(issues_clean):
    assert len(issues_clean) == 0


def test_every_in_scope_defect_is_caught_with_no_false_alarms(issues_defective, key):
    ev = evaluate.score(issues_defective, key)
    assert ev["defects_caught"] == ev["defects_in_scope"] == 74
    assert ev["defects_injected"] == 78 and ev["defects_out_of_scope"] == 4
    assert ev["false_alarms"] == 0 and ev["precision"] == 1.0 and ev["recall"] == 1.0


def test_out_of_scope_defects_are_not_detected(issues_defective, key):
    undetectable = key[~key["detectable"]]
    assert len(undetectable) == 4
    assert (undetectable["rule_id"] == "(none)").all()
    got = set(zip(issues_defective["template"], issues_defective["row"]))
    # the rows carrying the invisible defects stay silent
    assert not any((t, r) in got for t, r in zip(undetectable["template"], undetectable["row"]))


def test_score_drops_when_an_issue_is_removed(issues_defective, key):
    base = evaluate.score(issues_defective, key)
    fewer = evaluate.score(issues_defective.iloc[1:], key)
    assert fewer["recall"] < base["recall"]
    assert fewer["defects_caught"] < base["defects_caught"] or fewer["key_lines_hit"] < base["key_lines_hit"]


def test_score_drops_when_a_spurious_issue_is_added(issues_defective, key):
    extra = issues_defective.iloc[[0]].copy()
    extra["row"] = 9999
    ev = evaluate.score(pd.concat([issues_defective, extra], ignore_index=True), key)
    assert ev["false_alarms"] == 1 and ev["precision"] < 1.0


def test_key_rows_exist_in_the_tables(defective, key):
    det = key[key["detectable"] & (key["row"] > 0)]
    for r in det.itertuples():
        assert r.row <= len(defective[r.template]) + 1, (r.defect_id, r.template, r.row)


def test_by_rule_totals_match_the_score(issues_defective, key):
    per = evaluate.by_rule(issues_defective, key)
    ev = evaluate.score(issues_defective, key)
    assert per["hit"].sum() == ev["key_lines_hit"]
    assert per["false_alarms"].sum() == 0
    assert per["planted"].sum() == ev["key_lines_in_scope"]
