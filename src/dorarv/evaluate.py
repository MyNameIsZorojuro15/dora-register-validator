"""Score the validator against the answer key of the defective register."""
from __future__ import annotations

from typing import Dict

import pandas as pd


def score(issues: pd.DataFrame, key: pd.DataFrame) -> Dict[str, object]:
    """An issue is a hit when rule, template and row all match a key line that is meant to be detectable.
    A defect counts as caught when every detectable line of its key is hit."""
    det = key[key["detectable"]].copy()
    k = set(zip(det["rule_id"], det["template"], det["row"]))
    got = set(zip(issues["rule_id"], issues["template"], issues["row"]))
    hit = k & got
    false_alarms = sorted(got - k)
    det["hit"] = [(r, t, w) in got for r, t, w in zip(det["rule_id"], det["template"], det["row"])]
    caught = det.groupby("defect_id")["hit"].all()
    all_def = key.drop_duplicates("defect_id")
    n_def = len(all_def)
    n_det_def = int(all_def["detectable"].sum())
    out = {
        "defects_injected": n_def,
        "defects_in_scope": n_det_def,
        "defects_out_of_scope": n_def - n_det_def,
        "defects_caught": int(caught.sum()),
        "defects_missed_in_scope": int((~caught).sum()),
        "key_lines_in_scope": len(k),
        "key_lines_hit": len(hit),
        "issues_reported": len(got),
        "false_alarms": len(false_alarms),
        "precision": len(hit) / len(got) if got else 1.0,
        "recall": len(hit) / len(k) if k else 1.0,
        "false_alarm_list": [list(x) for x in false_alarms],
        "missed_list": sorted([list(x) for x in k - got]),
    }
    return out


def by_rule(issues: pd.DataFrame, key: pd.DataFrame) -> pd.DataFrame:
    det = key[key["detectable"]]
    k = set(zip(det["rule_id"], det["template"], det["row"]))
    got = set(zip(issues["rule_id"], issues["template"], issues["row"]))
    rules = sorted({r for r, _, _ in k | got})
    rows = []
    for r in rules:
        kr = {x for x in k if x[0] == r}
        gr = {x for x in got if x[0] == r}
        rows.append({"rule_id": r, "planted": len(kr), "reported": len(gr), "hit": len(kr & gr),
                     "missed": len(kr - gr), "false_alarms": len(gr - kr)})
    return pd.DataFrame(rows)
