import json
import re

import openpyxl
import pandas as pd

from dorarv import generate, readme, evaluate
from dorarv.reference import ROOT, load_real_leis
from dorarv.rules import RISK_FLAGS, RULES
from dorarv.validate import read_register, validate

from conftest import CLEAN, DEFECTIVE, REPORTS


def test_results_json_matches_a_fresh_validation(results, issues_clean, issues_defective, key):
    ev = evaluate.score(issues_defective, key)
    assert results["clean"]["issues"] == len(issues_clean) == 0
    assert results["defective"]["issues"] == len(issues_defective)
    for k in ("defects_injected", "defects_in_scope", "defects_caught", "false_alarms", "key_lines_hit"):
        assert results["evaluation"][k] == ev[k], k
    assert results["rules"]["data_quality"] == len(RULES)
    assert results["rules"]["risk_flags"] == len(RISK_FLAGS)


def test_readme_is_the_rendering_of_results_json(results):
    assert (ROOT / "README.md").read_text() == readme.render(results)


def test_readme_headline_numbers(results):
    text = (ROOT / "README.md").read_text()
    e = results["evaluation"]
    assert f"{e['defects_caught']} of {e['defects_injected']}" in text
    assert str(results["defective"]["issues"]) in text
    assert str(results["register"]["total_rows"]) in text
    assert "SYNTHETIC" in text


def test_readme_cites_sources():
    text = (ROOT / "README.md").read_text()
    for url in ("eur-lex.europa.eu", "eba.europa.eu", "gleif.org"):
        assert url in text
    assert len(re.findall(r"https://", text)) >= 5


def test_issue_csv_files_equal_the_validation(issues_defective, issues_clean):
    got = pd.read_csv(REPORTS / "issues_defective_register.csv", keep_default_na=False)
    assert len(got) == len(issues_defective)
    assert list(got.columns) == list(issues_defective.columns)
    assert (got["rule_id"].tolist() == issues_defective["rule_id"].tolist())
    assert (got["row"].tolist() == issues_defective["row"].tolist())
    assert len(pd.read_csv(REPORTS / "issues_clean_register.csv")) == 0


def test_excel_workbook(results, issues_defective):
    wb = openpyxl.load_workbook(REPORTS / "dora_register_issues.xlsx")
    assert wb.sheetnames == ["Summary", "Issues", "Risk flags", "Concentration - groups", "Concentration - countries",
                             "Critical functions", "Rules"]
    ws = wb["Issues"]
    header = [c.value for c in ws[1]]
    assert header[:4] == ["rule_id", "severity", "template", "row"] or {"rule_id", "severity", "row", "fix"} <= set(header)
    assert ws.max_row - 1 == len(issues_defective)
    assert {"analyst_status", "analyst_comment"} <= set(header)
    summary = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=2)}
    e = results["evaluation"]
    assert summary["Issues raised"] == results["defective"]["issues"]
    assert summary["Issues on the clean register"] == 0
    assert summary["Planted defects caught"] == f"{e['defects_caught']} of {e['defects_in_scope']}"
    assert wb["Rules"].max_row - 1 == len(RULES) + len(RISK_FLAGS)


def test_chart_exists():
    assert (REPORTS / "concentration.png").stat().st_size > 5_000


def test_generator_is_deterministic(tmp_path):
    tables = generate.build_clean()
    generate.write_register(tables, tmp_path / "clean", "x")
    for f in CLEAN.glob("B_*.csv"):
        assert (tmp_path / "clean" / f.name).read_bytes() == f.read_bytes(), f.name
    defective, key = generate.inject(generate.build_clean())
    generate.write_register(defective, tmp_path / "defective", "x")
    for f in DEFECTIVE.glob("B_*.csv"):
        assert (tmp_path / "defective" / f.name).read_bytes() == f.read_bytes(), f.name
    assert key.to_csv(index=False) == (DEFECTIVE / "answer_key.csv").read_text()


def test_registers_are_labelled_synthetic():
    for folder in (CLEAN, DEFECTIVE):
        m = json.loads((folder / "MANIFEST.json").read_text())
        assert m["synthetic"] is True and "SYNTHETIC" in m["notice"]


def test_synthetic_leis_are_not_real_leis(clean):
    real = {r["lei"] for r in load_real_leis()}
    leis = set()
    for df in clean.values():
        for col in df.columns:
            if col != "_row":
                leis |= {v for v in df[col] if re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", v or "")}
    assert leis and not (leis & real)
    assert all(v.startswith("SYNT") for v in leis)


def test_cli_validates_a_folder(tmp_path):
    from dorarv import cli
    out = tmp_path / "issues.csv"
    cli.main([str(DEFECTIVE), "--out", str(out)])
    assert len(pd.read_csv(out)) == len(validate(read_register(DEFECTIVE)))
