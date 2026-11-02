"""Rebuild everything: synthetic registers, validation, scoring, reports, results.json, README.md."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from . import concentration, evaluate, generate, report
from .model import TEMPLATES
from .reference import ROOT
from .rules import RISK_FLAGS, RULES
from .validate import read_register, validate

REPORTS = ROOT / "reports"


def run() -> dict:
    REPORTS.mkdir(exist_ok=True)
    generate.build_all()                       # writes data/synthetic/{clean,defective}
    key = pd.read_csv(generate.OUT / "defective" / "answer_key.csv")
    clean = read_register(generate.OUT / "clean")          # the validator reads the files, as an analyst would
    defective = read_register(generate.OUT / "defective")
    iss_clean = validate(clean)
    iss_def = validate(defective)
    ev = evaluate.score(iss_def, key)
    per_rule = evaluate.by_rule(iss_def, key)
    view = concentration.views(clean)
    flg = concentration.flags(view)
    cat = report.rule_catalogue()

    # files -----------------------------------------------------------------------------------------------------------
    iss_def.to_csv(REPORTS / "issues_defective_register.csv", index=False)
    iss_clean.to_csv(REPORTS / "issues_clean_register.csv", index=False)
    per_rule.to_csv(REPORTS / "evaluation_by_rule.csv", index=False)
    cat.to_csv(REPORTS / "rule_catalogue.csv", index=False)
    view["groups"].to_csv(REPORTS / "concentration_by_group.csv", index=False)
    view["countries"].to_csv(REPORTS / "concentration_by_country.csv", index=False)
    view["functions"].to_csv(REPORTS / "critical_function_dependency.csv", index=False)
    flg.to_csv(REPORTS / "risk_flags.csv", index=False)
    report.chart(REPORTS / "concentration.png", view["groups"], view["countries"])

    sev = iss_def["severity"].value_counts().to_dict()
    summary = pd.DataFrame([
        ("Register", "SYNTHETIC", f"{generate.GROUP}, reporting date {generate.REPORTING_DATE}"),
        ("Issues raised", len(iss_def), "defective register"),
        ("  errors", sev.get("error", 0), "format, key, mandatory-field and referential failures"),
        ("  warnings", sev.get("warning", 0), "business-logic and consistency findings"),
        ("Issues on the clean register", len(iss_clean), "false alarms"),
        ("Planted defects caught", f"{ev['defects_caught']} of {ev['defects_in_scope']}", "in scope for an offline rule set"),
        ("Planted defects out of scope", ev["defects_out_of_scope"], "need a registry lookup or a human"),
    ], columns=["metric", "value", "detail"])
    report.write_excel(REPORTS / "dora_register_issues.xlsx", iss_def, summary, view["groups"], view["countries"],
                       view["functions"], flg, cat)

    # numbers for the README ------------------------------------------------------------------------------------------
    n_rows = {c: len(df) for c, df in clean.items()}
    g = view["groups"]
    cty = view["countries"]
    up = cty[cty["basis"] == "ultimate parent headquarters"]
    nonEU = up[~up["in_eu"]]
    cats = Counter(r.category for r in RULES)
    basis = Counter(r.basis for r in RULES)
    key_rule = key[key["detectable"]].groupby("rule_id").size()
    cat_of = {r.id: r.category for r in RULES}
    pr = per_rule.assign(category=per_rule["rule_id"].map(cat_of))
    by_cat = {c: {"planted": int(x["planted"].sum()), "hit": int(x["hit"].sum()), "false_alarms": int(x["false_alarms"].sum()),
                  "rules": int(len(x))} for c, x in pr.groupby("category", sort=False)}
    results = {
        "register": {"group": generate.GROUP, "reporting_date": generate.REPORTING_DATE, "seed": generate.SEED,
                     "rows": n_rows, "total_rows": sum(n_rows.values()), "templates": len(TEMPLATES),
                     "entities": n_rows["B_01.02"], "contracts": int((clean["B_02.01"]["c0020"] != "Overarching/master agreement").sum()),
                     "providers": n_rows["B_05.01"], "functions": n_rows["B_06.01"],
                     "critical_functions": int((clean["B_06.01"]["c0050"] == "Yes").sum())},
        "rules": {"data_quality": len(RULES), "risk_flags": len(RISK_FLAGS),
                  "by_category": dict(cats), "by_basis": dict(basis),
                  "built_on_published_rule": sum(v for k, v in basis.items() if k.startswith("EBA")),
                  "rules_in_sql": int(sum(1 for r in RULES if r.category in ("Referential integrity", "Cross-template")))},
        "clean": {"issues": len(iss_clean)},
        "defective": {"issues": len(iss_def), "errors": sev.get("error", 0), "warnings": sev.get("warning", 0),
                      "rules_fired": int(iss_def["rule_id"].nunique()),
                      "by_template": {k: int(v) for k, v in iss_def["template"].value_counts().sort_index().items()}},
        "evaluation": {k: v for k, v in ev.items() if not k.endswith("_list")},
        "evaluation_by_category": by_cat,
        "undetectable": [{"defect_id": r.defect_id, "defect": r.defect, "template": r.template, "row": int(r.row)}
                         for r in key[~key["detectable"]].itertuples()],
        "planted_by_rule": {k: int(v) for k, v in key_rule.items()},
        "concentration": {
            "spend_eur": float(g["spend_eur"].sum()), "groups": len(g),
            "top_group": g.iloc[0]["group_name"], "top_group_share": float(g.iloc[0]["spend_share"]),
            "top_group_critical_functions": int(g.iloc[0]["critical_functions"]),
            "top3_share": float(g["spend_share"].head(3).sum()),
            "top_parent_country_non_eu": nonEU.iloc[0]["country"], "top_parent_country_non_eu_share": float(nonEU.iloc[0]["spend_share"]),
            "flags": {k: int(v) for k, v in flg["flag_id"].value_counts().sort_index().items()},
            "single_provider_functions": int(view["functions"]["single_provider"].sum()),
            "critical_functions": len(view["functions"]),
            "top_groups": g.head(5)[["group_name", "group_country", "spend_eur", "spend_share", "critical_functions"]].to_dict("records"),
        },
        "examples": iss_def[iss_def["rule_id"].isin(["DRV-05", "DRV-31", "DRV-45", "DRV-46", "DRV-43"])
                            & ~iss_def["message"].str.contains("add up to -")]
        .drop_duplicates("rule_id")[["severity", "rule_id", "template", "row", "message", "fix"]].to_dict("records"),
    }
    (REPORTS / "results.json").write_text(json.dumps(results, indent=2, default=float) + "\n")
    from . import readme
    (ROOT / "README.md").write_text(readme.render(results))
    return results


if __name__ == "__main__":
    r = run()
    e = r["evaluation"]
    print(f"caught {e['defects_caught']} of {e['defects_injected']} injected defects "
          f"({e['defects_out_of_scope']} out of scope); false alarms on clean: {r['clean']['issues']}; "
          f"precision {e['precision']:.3f}, recall {e['recall']:.3f}")
