"""Each rule fires on a hand-made defect and stays silent on the clean register.

The mutations below are written by hand against the clean register, independently of the generator that plants
the defects for the answer key. Row numbers are 0-based data rows (CSV line = row + 2). Every case lists the full
set of issues it should cause, cascades included, and the test compares the whole set.
"""
import pytest

from dorarv import checks
from dorarv.model import TEMPLATES
from dorarv.rules import BY_ID, RULES
from dorarv.validate import validate
from conftest import hits, mutated

E1 = lambda t: t["B_01.01"].at[0, "c0010"]            # noqa: E731
E2 = lambda t: t["B_01.02"].at[1, "c0010"]            # noqa: E731
LOWER = lambda t: t["B_01.02"].at[1, "c0060"].lower()  # noqa: E731
NOTAREG = "SYNT0000000000000000"                       # placeholder, replaced below by a valid unregistered LEI


def _valid_unregistered():
    from dorarv import lei
    import random
    return lei.make_lei(random.Random(99), "SYNT")


UNREG = _valid_unregistered()

CASES = {
    "mandatory blank": ([("B_05.01", 0, "c0050", "")], {("DRV-02", "B_05.01", 0)}),
    "duplicate key": ([("B_01.03", 2, "c0010", "BR-E1-FR01"), ("B_01.03", 2, "c0020", E1)],
                      {("DRV-03", "B_01.03", 0), ("DRV-03", "B_01.03", 2)}),
    "lei lower case": ([("B_01.02", 1, "c0060", LOWER)], {("DRV-04", "B_01.02", 1)}),
    "lei too short": ([("B_01.02", 1, "c0060", lambda t: t["B_01.02"].at[1, "c0060"][:19])], {("DRV-04", "B_01.02", 1)}),
    "lei check digits": ([("B_01.02", 1, "c0060", lambda t: t["B_01.02"].at[1, "c0060"][:18] + "00")],
                         {("DRV-05", "B_01.02", 1)}),
    "country uk": ([("B_05.01", 8, "c0080", "UK")], {("DRV-06", "B_05.01", 8)}),
    "country three letters": ([("B_01.03", 0, "c0040", "FRA")], {("DRV-06", "B_01.03", 0)}),
    "currency": ([("B_01.02", 0, "c0100", "EURO")], {("DRV-07", "B_01.02", 0)}),
    "provider declared euid, is lei": ([("B_05.01", 1, "c0020", "EUID")], {("DRV-08", "B_05.01", 1)}),
    "provider declared lei, is euid": ([("B_05.01", 14, "c0020", "LEI")], {("DRV-08", "B_05.01", 14)}),
    "closed list": ([("B_01.02", 1, "c0040", "Bank")], {("DRV-09", "B_01.02", 1)}),
    "boolean": ([("B_07.01", 0, "c0080", "maybe")], {("DRV-09", "B_07.01", 0)}),
    "date format": ([("B_06.01", 0, "c0070", "15/03/2025")], {("DRV-10", "B_06.01", 0)}),
    "date impossible": ([("B_06.01", 0, "c0070", "2025-02-30")], {("DRV-10", "B_06.01", 0)}),
    "integer": ([("B_06.01", 0, "c0080", "4h")], {("DRV-11", "B_06.01", 0)}),
    "amount with comma": ([("B_01.02", 0, "c0110", "1,5")], {("DRV-11", "B_01.02", 0)}),
    "negative total assets": ([("B_01.02", 0, "c0110", "-5")], {("DRV-12", "B_01.02", 0)}),
    "end before start": ([("B_02.02", 0, "c0080", "2010-01-01")], {("DRV-13", "B_02.02", 0)}),
    "assessment in the future": ([("B_06.01", 0, "c0070", "2026-06-01")], {("DRV-14", "B_06.01", 0)}),
    "deleted before integrated": ([("B_01.02", 1, "c0090", "2024-12-31")], {("DRV-15", "B_01.02", 1)}),
    "reason without end": ([("B_02.02", 0, "c0090", "Expired")], {("DRV-16", "B_02.02", 0)}),
    "assets without currency": ([("B_01.02", 0, "c0100", "")], {("DRV-17", "B_01.02", 0)}),
    "subsequent without master": ([("B_02.01", 3, "c0030", "")], {("DRV-18", "B_02.01", 3)}),
    "branch flag without code": ([("B_04.01", 0, "c0030", "true")], {("DRV-19", "B_04.01", 0)}),
    "hard to substitute without reason": ([("B_07.01", 0, "c0060", "")], {("DRV-20", "B_07.01", 0)}),
    "critical without reasons": ([("B_06.01", 0, "c0060", "")], {("DRV-21", "B_06.01", 0)}),
    "alternatives flag without name": ([("B_07.01", 1, "c0110", "true"), ("B_07.01", 1, "c0120", "")],
                                       {("DRV-22", "B_07.01", 1)}),
    "storage without location": ([("B_02.02", 1, "c0150", "")], {("DRV-23", "B_02.02", 1)}),
    "unknown contract": ([("B_03.01", 5, "c0010", "RC-0000")],
                         {("DRV-30", "B_03.01", 5), ("DRV-40", "B_02.01", 5)}),
    "unknown entity": ([("B_06.01", 0, "c0040", UNREG)], {("DRV-31", "B_06.01", 0)}),
    "unknown provider in supply chain": ([("B_05.02", 0, "c0060", UNREG)], {("DRV-32", "B_05.02", 0)}),
    "unknown function": ([("B_02.02", 3, "c0050", "F9999")], {("DRV-33", "B_02.02", 3)}),
    "assessment without matching contract row": ([("B_07.01", 0, "c0020", lambda t: t["B_05.01"].at[1, "c0010"])],
                                                  {("DRV-34", "B_07.01", 0)}),
    "overarching points to a standalone": ([("B_02.01", 3, "c0030", "RC-0003")], {("DRV-35", "B_02.01", 3)}),
    "unknown branch": ([("B_04.01", 0, "c0030", "true"), ("B_04.01", 0, "c0040", "BR-XX-00")], {("DRV-36", "B_04.01", 0)}),
    "contract without satellite rows": ([("B_03.02", 6, "c0010", "RC-0000")],
                                        {("DRV-30", "B_03.02", 6), ("DRV-40", "B_02.01", 6), ("DRV-46", "B_05.01", 17)}),
    "provider differs between B_02.02 and B_03.02": ([("B_02.02", 4, "c0030", UNREG)],
                                                     {("DRV-32", "B_02.02", 4), ("DRV-41", "B_02.02", 4), ("DRV-34", "B_05.02", 2),
                                                      ("DRV-34", "B_07.01", 4)}),
    "assessment for a non-critical contract": ([("B_07.01", 0, "c0010", "RC-0007")],
                                               {("DRV-34", "B_07.01", 0), ("DRV-43", "B_07.01", 0),
                                                ("DRV-43", "B_02.02", 0)}),
    "reliance filled for a non-critical function": ([("B_02.02", 6, "c0180", "Low reliance")], {("DRV-44", "B_02.02", 6)}),
    "no exit plan": ([("B_07.01", 0, "c0080", "false")], {("DRV-45", "B_07.01", 0)}),
    "provider total off": ([("B_05.01", 1, "c0100", "1")], {("DRV-46", "B_05.01", 1)}),
    "rank gap": ([("B_05.02", 1, "c0050", "3")], {("DRV-47", "B_05.02", 1)}),
    "own sub-contractor": ([("B_05.02", 0, "c0060", lambda t: t["B_05.02"].at[0, "c0030"])], {("DRV-47", "B_05.02", 0)}),
}


def test_clean_register_raises_nothing(issues_clean):
    assert len(issues_clean) == 0


@pytest.mark.parametrize("name", list(CASES))
def test_rule_fires_on_the_defect_and_nothing_else(clean, name):
    edits, expected = CASES[name]
    got = hits(validate(mutated(clean, edits)))
    assert got == expected, (sorted(got - expected), sorted(expected - got))


def test_cases_cover_every_rule_except_the_ones_tested_elsewhere():
    covered = {rule for _, exp in CASES.values() for rule, _, _ in exp}
    assert {r.id for r in RULES} - covered - {"DRV-01", "DRV-42"} == set()


def test_unused_provider_is_flagged_but_an_ultimate_parent_is_not(clean):
    t = mutated(clean, [("B_03.02", 0, "c0010", "RC-0000")])   # the only B_03.02 row of RC-M001 (provider 0)
    # provider 0 still has other contracts, so it stays used
    assert not any(i.rule_id == "DRV-42" for i in validate(t).itertuples())
    t = mutated(clean, [("B_05.01", 22, "c0010", clean["B_05.01"].at[22, "c0010"]), ("B_05.01", 0, "c0110", "")])
    got = hits(validate(t))
    assert ("DRV-42", "B_05.01", 22) in got          # Aurelia Holdings is no longer anybody's parent and has no contract


@pytest.mark.parametrize("code", list(TEMPLATES))
def test_empty_template_is_reported(clean, code):
    t = {k: v.copy() for k, v in clean.items()}
    t[code] = t[code].iloc[0:0]
    got = validate(t)
    assert ((got["rule_id"] == "DRV-01") & (got["template"] == code)).sum() == 1


def test_missing_file_is_read_as_an_empty_template(tmp_path):
    from dorarv.validate import validate_folder
    got = validate_folder(tmp_path)
    assert set(got["template"]) == set(TEMPLATES) and set(got["rule_id"]) == {"DRV-01"}


def test_every_rule_fires_somewhere_in_the_defective_register(issues_defective):
    assert {r.id for r in RULES} - set(issues_defective["rule_id"]) == {"DRV-01"}


def test_issue_table_shape_and_catalogue(issues_defective):
    assert list(issues_defective.columns) == ["rule_id", "severity", "template", "row", "key", "column", "value",
                                              "message", "fix", "eba_ref", "basis"]
    assert set(issues_defective["severity"]) <= {"error", "warning"}
    assert issues_defective["rule_id"].isin(BY_ID).all()
    assert (issues_defective["fix"].str.len() > 10).all() and (issues_defective["message"].str.len() > 5).all()
    assert issues_defective["severity"].is_monotonic_increasing or issues_defective.iloc[0]["severity"] == "error"
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids)) and all(i.startswith("DRV-") for i in ids)


def test_published_rule_ids_cited_exist_in_the_ebas_workbook_extract():
    """The IDs quoted in the catalogue were read from the EBA overview workbook (28 April 2025)."""
    import re
    ids = set()
    for r in RULES:
        ids |= set(re.findall(r"\b(?:v\d+_[a-z]|e\d+_e|VR_\d+)\b", r.eba_ref))
    expected = {"e23674_e", "e23675_e", "e23676_e", "e23677_e", "e23680_e", "e23682_e", "e23683_e", "e23792_e", "e23681_e",
                "v8850_m", "v8855_m", "v8858_m", "v8865_m", "v8866_m", "v8868_m", "v8869_m", "v8871_m", "v8872_m", "v8876_m",
                "v8877_m", "v8883_m", "v8884_m", "v8886_m", "v8888_m", "v88889_m", "v8826_m", "v8890_m", "v8891_m", "v8892_m",
                "VR_2", "VR_12", "VR_16", "VR_23", "VR_71", "VR_72", "VR_77", "VR_78", "v8821_m", "v22913_s", "v23716_s", "v8816_m",
                "v8803_m", "v8805_m", "v22912_m", "v8825_m"}
    assert ids == expected


def test_parse_date_accepts_only_real_dates():
    assert checks.parse_date("2024-02-29") and not checks.parse_date("2025-02-29")
    assert not checks.parse_date("2025-2-9") and not checks.parse_date("") and not checks.parse_date("2025-13-01")
