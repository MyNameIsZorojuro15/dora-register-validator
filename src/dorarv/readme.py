"""Render README.md from results.json, so that no figure in the text is typed by hand."""
from __future__ import annotations

from .reference import THRESHOLDS

ELI_ITS = "https://eur-lex.europa.eu/eli/reg_impl/2024/2956/oj"
ELI_DORA = "https://eur-lex.europa.eu/eli/reg/2022/2554/oj"
EBA_PAGE = "https://www.eba.europa.eu/activities/direct-supervision-and-oversight/digital-operational-resilience-act/preparation-dora-application"
EBA_MODEL = "https://www.eba.europa.eu/sites/default/files/2025-04/035dd2b6-c7e3-4c7d-954f-6ffd41903de2/Data%20Model%20for%20DORA%20RoI.pdf"
EBA_RULES = ("https://www.eba.europa.eu/sites/default/files/2025-04/10100a51-275f-4c98-96a1-f81342a8f57d/"
             "Overview%20of%20the%20RoI%20reporting%20technical%20checks%20and%20validation%20rules%20%28updated%2028%20April%202025%29%20%284%29.xlsx")
EBA_REVISED = "https://www.eba.europa.eu/publications-and-media/press-releases/eba-issues-revised-list-its-validation-rules-and-announces-new-website-location"
GLEIF = "https://www.gleif.org/en/about-lei/iso-17442-the-lei-code-structure"


def _m(x: float, d: int = 1) -> str:
    return f"{x / 1e6:,.{d}f}"


def _p(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f} %"


def render(r: dict) -> str:
    reg, ru, ev, cl, de, co = r["register"], r["rules"], r["evaluation"], r["clean"], r["defective"], r["concentration"]
    bc = r["evaluation_by_category"]
    basis = ru["by_basis"]
    t_cat = "\n".join(f"| {c} | {v['rules']} | {v['planted']} | {v['hit']} | {v['false_alarms']} |" for c, v in bc.items())
    t_rules = "\n".join(f"| {c} | {n} |" for c, n in ru["by_category"].items())
    t_oos = "\n".join(f"| {u['defect_id']} | {u['defect']} | {u['template']} row {u['row']} |" for u in r["undetectable"])
    t_tpl = "\n".join(f"| {k} | {v} |" for k, v in de["by_template"].items())
    t_ex = "\n".join(f"| {e['severity']} | {e['rule_id']} | {e['template']} row {e['row']} | {e['message']} | {e['fix']} |"
                     for e in r["examples"])
    t_top = "\n".join(f"| {g['group_name']} | {g['group_country']} | {_m(g['spend_eur'])} | {_p(g['spend_share'])} | {g['critical_functions']} |"
                      for g in co["top_groups"])
    fl = co["flags"]
    t_rows = ", ".join(f"{k} {v}" for k, v in reg["rows"].items())

    return f"""# DORA Register of Information: a validator measured against planted defects

A third-party-risk case. Under DORA (Regulation (EU) 2022/2554, Art. 28(3)) a financial entity keeps a register of all its
contractual arrangements with ICT third-party service providers and reports it to its supervisor. Before it does, can the
entity's own data pass the checks the supervisor will apply, and which providers is it most dependent on? This project
re-implements a subset of the published validation rules, runs them against a synthetic register with defects planted at known
places, and measures how many are found and how many alarms are false.

**Headline:** the validator caught **{ev['defects_caught']} of {ev['defects_injected']} planted defects**, with **{cl['issues']} false alarms on the clean register**
({reg['total_rows']} rows, {reg['templates']} templates). {ev['defects_out_of_scope']} of the {ev['defects_injected']} defects cannot be seen by an offline rule set
by design (they need a registry lookup or a human) and are counted as missed; the other {ev['defects_in_scope']} were all caught. On the defective
register it raised {de['issues']} issues, every one of them on the answer key (precision {ev['precision']:.2f}, recall {ev['recall']:.2f} on the lines that can be detected).
{ru['data_quality']} data-quality rules and {ru['risk_flags']} concentration flags are implemented;
{ru['built_on_published_rule']} of the {ru['data_quality']} rules are built on a published EBA rule or technical check, quoted by ID.

| Deliverable | File |
|---|---|
| Issues report for a TPRM analyst: rule, severity, template, row, key, value, fix, EBA reference, with status and comment columns (Excel) | [`reports/dora_register_issues.xlsx`](reports/dora_register_issues.xlsx) |
| The same issues as CSV, and the clean-register run (empty) | [`reports/issues_defective_register.csv`](reports/issues_defective_register.csv), [`reports/issues_clean_register.csv`](reports/issues_clean_register.csv) |
| Concentration view: spend and criticality by provider group and by country, risk flags | [`reports/concentration.png`](reports/concentration.png), [`reports/concentration_by_group.csv`](reports/concentration_by_group.csv), [`reports/concentration_by_country.csv`](reports/concentration_by_country.csv), [`reports/risk_flags.csv`](reports/risk_flags.csv) |
| Rule catalogue with the published rule IDs | [`reports/rule_catalogue.csv`](reports/rule_catalogue.csv) |
| Answer key and per-rule scoring | [`data/synthetic/defective/answer_key.csv`](data/synthetic/defective/answer_key.csv), [`reports/evaluation_by_rule.csv`](reports/evaluation_by_rule.csv) |
| All numbers quoted here | [`reports/results.json`](reports/results.json) |
| SQL (DuckDB): referential integrity, cross-template consistency, concentration | [`sql/`](sql/) |

![Concentration](reports/concentration.png)

## Data

**Real and public (rules, structure, reference):**

| What | Source |
|---|---|
| Templates B_01.01 to B_07.01 and their content: Commission Implementing Regulation (EU) 2024/2956 (ITS on the register of information) | [{ELI_ITS}]({ELI_ITS}) |
| The register obligation and the concentration and exit-strategy provisions (Art. 28, 29) | [DORA, Regulation (EU) 2022/2554]({ELI_DORA}) |
| Columns, keys, nullability and data types per template | [EBA, Data Model for DORA RoI (April 2025)]({EBA_MODEL}) |
| Technical checks, DPM business validation rules and LEI/EUID/country checks, with their IDs | [EBA, Overview of the RoI reporting technical checks and validation rules (updated 28 April 2025)]({EBA_RULES}) |
| Index of all EBA reporting material for the register (data point model, taxonomy, filing rules, FAQ) | [{EBA_PAGE}]({EBA_PAGE}) |
| LEI structure (ISO 17442) | [GLEIF]({GLEIF}) |
| Six real, public LEIs, used only as test vectors for the check digits | [`data/reference/real_lei_samples.csv`](data/reference/real_lei_samples.csv) |

The EBA overview workbook lists 29 reception and CSV technical checks, 12 DPM technical checks, 71 DPM business validation rules (58 active,
13 inactive) and 8 LEI, EUID and country checks. The column codes (c0010, c0020 ...) in the synthetic files are the EBA's own.

**Synthetic (the register under test):** `{reg['group']}`, reference date {reg['reporting_date']}, generated by
[`src/dorarv/generate.py`](src/dorarv/generate.py) with a fixed seed. Every name, code and amount is invented; the LEIs carry valid check
digits and the prefix SYNT and are not registered anywhere. No real company data is presented as real.

| | Clean register | Defective register |
|---|---|---|
| Files | [`data/synthetic/clean/`](data/synthetic/clean/) | [`data/synthetic/defective/`](data/synthetic/defective/) |
| Rows per template | {t_rows} | the same, plus a few appended rows |
| Contents | {reg['entities']} entities, {reg['contracts']} contracts (plus 3 master agreements), {reg['providers']} providers, {reg['functions']} functions ({reg['critical_functions']} critical), supply chains, assessments | {ev['defects_injected']} planted defects, see `answer_key.csv` |

## Results

### 1. The rule set

{ru['data_quality']} data-quality rules across {len(ru['by_category'])} families, {ru['rules_in_sql']} of them in DuckDB SQL because they join templates:

| Family | Rules |
|---|---:|
{t_rules}

How close each rule is to the published one (column `basis` in the catalogue):

| Basis | Rules | Meaning |
|---|---:|---|
| EBA | {basis.get('EBA', 0)} | A published rule or technical check, same logic |
| EBA-family | {basis.get('EBA-family', 0)} | A family of published rules with one shared logic, implemented once |
| EBA-offline | {basis.get('EBA-offline', 0)} | A published rule that needs the GLEIF or BRIS register; an offline proxy is implemented |
| EBA-inactive | {basis.get('EBA-inactive', 0)} | A published rule the EBA deactivated in March 2025, kept as a data-quality rule |
| ITS | {basis.get('ITS', 0)} | Follows the templates or DORA text, no published rule ID |
| custom | {basis.get('custom', 0)} | This project's own consistency check |

The EBA marks every DPM business rule as a warning; the `error` / `warning` column here is a separate judgement: error means the value is unusable or the file
would not load (format, key, mandatory field, foreign key), warning means a business-logic or consistency finding.

### 2. Measured against the answer key (defective register)

| | |
|---|---:|
| Defects planted | {ev['defects_injected']} |
| In scope for an offline rule set | {ev['defects_in_scope']} |
| Caught | {ev['defects_caught']} |
| Key lines (rule, template, row) that should be raised | {ev['key_lines_in_scope']} |
| Key lines raised | {ev['key_lines_hit']} |
| Issues raised in total | {ev['issues_reported']} |
| False alarms (issues not on the key) | {ev['false_alarms']} |
| False alarms on the clean register | {cl['issues']} |

A defect is caught only when every issue it should cause is raised. {ev['defects_injected']} defects give {ev['key_lines_in_scope']} key lines because some defects legitimately trigger
several rules: an LEI typo breaks the check digits and the foreign key, a provider total off by 25 % breaks the reconciliation.

| Rule family | Rules planted against | Planted | Raised on target | False alarms |
|---|---:|---:|---:|---:|
{t_cat}

DRV-01 (empty template) cannot be planted without deleting a file, so it is tested in `tests/` only. The {ev['defects_out_of_scope']} defects outside the reach of the rules, all missed:

| ID | Defect | Where |
|---|---|---|
{t_oos}

These are the useful ones to read. A well-formed LEI with correct check digits can still belong to the wrong company; two numbers that agree can both be wrong; a
valid country code can be the wrong one. Offline rules do not find these, a GLEIF lookup or a reviewer with the contract might.
Because the same author wrote the rules and the key, the score shows that the implementation does what was intended, not that real registers hold no other kind of defect (see limits).

### 3. What the analyst gets

{de['issues']} issues on the defective register: {de['errors']} errors and {de['warnings']} warnings, from {de['rules_fired']} different rules. Each row carries the rule, the severity, the template, the CSV
row, the key of the record, the offending value, a message, a suggested fix and the EBA reference. Issues by template:

| Template | Issues |
|---|---:|
{t_tpl}

Examples (the fix column is what the analyst sees):

| Severity | Rule | Where | Message | Fix |
|---|---|---|---|---|
{t_ex}

### 4. Concentration (clean register)

Total annual ICT spend {_m(co['spend_eur'])} m EUR (fixed illustrative exchange rates), {co['groups']} provider groups after rolling providers up to their ultimate parent.
**{co['top_group']} takes {_p(co['top_group_share'])} of the spend and supports {co['top_group_critical_functions']} critical functions**; the top three groups take {_p(co['top3_share'])}.
By country of the ultimate parent, **{co['top_parent_country_non_eu']} accounts for {_p(co['top_parent_country_non_eu_share'])}**, although the largest provider is incorporated in Ireland.

| Provider group (ultimate parent) | Country | Spend, EUR m | Share | Critical functions supported |
|---|---|---:|---:|---:|
{t_top}

{co['single_provider_functions']} of {co['critical_functions']} critical functions depend on a single provider.
Flags raised (thresholds are illustrative, not regulatory): CON-01 provider group at or above {THRESHOLDS['provider_spend_share']:.0%} of spend: {fl.get('CON-01', 0)};
CON-02 group supporting {THRESHOLDS['critical_functions_supported']} or more critical functions: {fl.get('CON-02', 0)};
CON-03 one non-EU jurisdiction at or above {THRESHOLDS['third_country_spend_share']:.0%} of spend: {fl.get('CON-03', 0)}; CON-04 critical function with one provider: {fl.get('CON-04', 0)}.
Flags are risk signals for a review, not data errors, so they sit in their own sheet and do not count as validator issues.

## Method

| Step | File |
|---|---|
| Data model (columns, kinds, keys) taken from the EBA data model | [`src/dorarv/model.py`](src/dorarv/model.py) |
| Rule catalogue with published IDs, basis and fix text | [`src/dorarv/rules.py`](src/dorarv/rules.py) |
| Single-template rules: mandatory fields, keys, LEI format and check digits, country, currency, dates, numbers, closed lists, conditional fields | [`src/dorarv/checks.py`](src/dorarv/checks.py), [`src/dorarv/lei.py`](src/dorarv/lei.py) |
| Cross-template rules in DuckDB: foreign keys, contract-provider-function consistency, criticality and substitutability, exit plans, expense reconciliation, supply chain | [`sql/10_referential.sql`](sql/10_referential.sql), [`sql/20_consistency.sql`](sql/20_consistency.sql) |
| Concentration by group, country and critical function | [`sql/30_concentration_by_group.sql`](sql/30_concentration_by_group.sql), [`sql/31_concentration_by_country.sql`](sql/31_concentration_by_country.sql), [`sql/32_critical_function_dependency.sql`](sql/32_critical_function_dependency.sql), [`src/dorarv/concentration.py`](src/dorarv/concentration.py) |
| Synthetic register, defect injection, answer key | [`src/dorarv/generate.py`](src/dorarv/generate.py) |
| Scoring against the key | [`src/dorarv/evaluate.py`](src/dorarv/evaluate.py) |
| Reports, Excel, chart, this README | [`src/dorarv/report.py`](src/dorarv/report.py), [`build.py`](src/dorarv/build.py), [`readme.py`](src/dorarv/readme.py) |
| Validate any folder of template CSVs | `python -m dorarv.cli <folder> --out issues.csv` |
| Tests: every rule fires on a planted defect and stays silent on the clean register, LEI check digits (real and generated codes), rule IDs exist in the catalogue, SQL runs, README figures equal `results.json` | [`tests/`](tests/) |

Choices worth defending:

- **The key is scored per rule, template and row**, not per file. A validator that says "something is wrong somewhere" would score full marks per file and be useless to an analyst.
- **Cascades are written into the key.** A planted LEI typo must produce both the check-digit issue and the foreign-key issue; anything else on the report is a false alarm.
- **Out-of-scope defects are planted on purpose and counted as misses.** Without them a score of {ev['defects_caught']} of {ev['defects_injected']} would be easy and uninformative.
- **Foreign keys are checked with anti-joins on text keys**, not joins, so a duplicate row cannot fan out and create or hide issues.
- **Contract to provider comes from B_03.02** (the signing provider); B_02.02 must agree with it (DRV-41), and spend is reconciled on that mapping.
- **Roll-up to the ultimate parent** before measuring concentration: two providers owned by one group are one dependency.

## Limits

- **The key and the rules have the same author.** Perfect precision and recall show the code does what was intended on {ev['defects_injected']} planted cases, not that it finds every defect a real register would hold. A real register will contain failure types not planted here.
- **Offline only.** No GLEIF or BRIS lookup: check digits catch typos, not LEIs that are well-formed but unregistered, lapsed, or someone else's (the out-of-scope list above).
- **Closed lists are simplified labels.** The official submission uses DPM member codes and the full lists; the meaning of one member (x3 as "subsequent or associated arrangement") is inferred from rule v8805_m. The EBA 'list of possible values' file was not loaded.
- **Packaging checks are out of scope**: file names, the zip, report.json, filing indicators, parameters.csv (technical checks 1xx and 7xx), and the xBRL-CSV taxonomy validation.
- **Rule status moves.** IDs and status are from the overview dated 28 April 2025. The EBA published a [revised list in December 2025]({EBA_REVISED}) that was not checked here. Rules v8816_m (DRV-13) and v8821_m (DRV-08) are inactive in that workbook and are kept as data-quality rules; the existence rule for B_07.01 (e23681_e) is inactive but DRV-01 still checks B_07.01.
- **Twelve of the fourteen templates**: B_02.03 and B_03.03 (intra-group arrangements) are not generated or validated.
- **Column meanings come from the data model labels**, for example the roles of provider and recipient in B_05.02. Check them against the instructions in the annexes of the ITS before using the rules on a real register.
- **Reconciliation assumes one provider per contract** and skips providers whose contract currency differs from the provider's currency. Exchange rates in the concentration view are fixed and illustrative; thresholds for the flags are illustrative.
- **Small data.** {reg['total_rows']} rows. Real registers are larger; speed and memory were not tested at that size.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python -m dorarv.build      # synthetic registers, issues, answer-key score, concentration, workbook, results.json, this README
python -m pytest -q
python -m dorarv.cli data/synthetic/defective --out issues.csv     # validate any folder of template CSVs
```

Every number above comes from `reports/results.json`, produced by `python -m dorarv.build`, and a test fails if this README and the code disagree.
"""
