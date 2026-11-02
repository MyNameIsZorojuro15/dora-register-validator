"""Catalogue of the data-quality rules and the concentration flags.

`eba_ref` lists the published rule IDs a rule is built from (file 'Overview of the RoI reporting technical checks and
validation rules', updated 28 April 2025). Numeric codes are technical checks, 'v...' and 'e...' codes are DPM business
rules, 'VR_' codes are the LEI/EUID/country business checks. `basis` says how close the rule is to the published one:
  EBA          the published rule, same logic
  EBA-offline  the published rule needs an external register (GLEIF); an offline proxy is implemented
  EBA-family   a family of published rules with one shared logic, implemented once
  EBA-inactive the published rule was deactivated by the EBA in March 2025; kept as a data-quality rule
  ITS          follows the templates or DORA text but has no published rule ID
  custom       this project's own consistency check
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    category: str
    severity: str        # error: structural or format failure, the file would not load or the value is unusable
    #                      warning: business-logic or consistency finding
    templates: str
    eba_ref: str
    basis: str
    fix: str


R = Rule
RULES: List[Rule] = [
    R("DRV-01", "Template is empty", "Completeness", "error", "all", "e23674_e, e23675_e, e23676_e, e23677_e, e23680_e, e23682_e, e23683_e, e23792_e; 808 (e23681_e for B_07.01 is inactive since March 2025, still checked here)", "EBA-family",
      "Report the template with at least one row; every template is expected in the package."),
    R("DRV-02", "Mandatory field is blank", "Completeness", "error", "all", "805; v8850_m-v8855_m, v8858_m-v8865_m, v8866_m-v8868_m, v8869_m-v8871_m, v8872_m-v8876_m, v8877_m-v8883_m, v8884_m-v8886_m, v8888_m, v88889_m", "EBA-family",
      "Fill the field from the contract file or the entity master data."),
    R("DRV-03", "Duplicate key", "Completeness", "error", "all", "806", "EBA",
      "Keep one row per key; merge or delete the duplicate."),
    R("DRV-04", "LEI has the wrong format", "Format", "error", "B_01.01, B_01.02, B_01.03, B_02.02, B_03.01, B_04.01, B_05.01, B_05.02, B_06.01, B_07.01", "v8826_m, v8890_m, v8891_m, v8892_m", "EBA",
      "An LEI has 18 letters or digits (upper case) followed by 2 check digits. Copy it from the GLEIF record."),
    R("DRV-05", "LEI check digits are wrong", "Format", "error", "same as DRV-04", "VR_2, VR_12, VR_23, VR_71, VR_77", "EBA-offline",
      "The ISO 17442 check digits do not match: a typo. Copy the LEI from the GLEIF record."),
    R("DRV-06", "Country code is not ISO 3166-1 alpha-2", "Format", "error", "B_01.01, B_01.02, B_01.03, B_02.02, B_05.01", "VR_16", "EBA-offline",
      "Use the 2-letter code (GB, not UK; DE, not DEU)."),
    R("DRV-07", "Currency code is not ISO 4217", "Format", "error", "B_01.02, B_02.01, B_05.01", "(data model: char(3))", "ITS",
      "Use the 3-letter code (EUR, USD)."),
    R("DRV-08", "Provider code does not match its declared type", "Format", "error", "B_02.02, B_03.02, B_05.01, B_05.02, B_07.01", "VR_71, VR_72, VR_77, VR_78; v8821_m (inactive)", "EBA-offline",
      "Declare LEI for a 20-character LEI and EUID for a code like DEK1101R.HRB123456, and fix the value if it is neither."),
    R("DRV-09", "Value is not in the closed list", "Format", "error", "all", "503; 332", "EBA-family",
      "Pick one of the allowed values (see the reference lists)."),
    R("DRV-10", "Date is not a valid yyyy-mm-dd date", "Format", "error", "all with dates", "330", "EBA",
      "Use ISO format yyyy-mm-dd and a real calendar date."),
    R("DRV-11", "Number is not a whole number or amount", "Format", "error", "all with numbers", "305, 331", "EBA",
      "Enter digits only (no text, units or thousands separators)."),
    R("DRV-12", "Amount is negative", "Format", "warning", "B_01.02, B_02.01, B_05.01", "v22913_s, v23716_s", "EBA",
      "Expenses and total assets cannot be negative. Check the sign or the source."),
    R("DRV-13", "End date is not after the start date", "Date logic", "warning", "B_02.02", "v8816_m", "EBA-inactive",
      "Correct the dates against the signed contract."),
    R("DRV-14", "Date is after the reporting date", "Date logic", "warning", "B_01.02, B_06.01, B_07.01", "111 (same idea for the filename date)", "ITS",
      "An assessment, audit or update cannot be dated after the reference date. Correct the date."),
    R("DRV-15", "Entity lifecycle dates are inconsistent", "Date logic", "warning", "B_01.02", "(none)", "custom",
      "Order must be integration <= last update and integration <= deletion."),
    R("DRV-16", "Termination reason without an end date", "Date logic", "warning", "B_02.02", "(none)", "custom",
      "Add the end date, or remove the reason if the contract is still running."),
    R("DRV-17", "Amount reported without a currency", "Conditional", "error", "B_01.02, B_05.01", "v8803_m", "EBA",
      "Add the currency of the amount."),
    R("DRV-18", "Subsequent arrangement has no overarching reference", "Conditional", "error", "B_02.01", "v8805_m, v22912_m", "EBA",
      "Fill the reference number of the master agreement."),
    R("DRV-19", "Branch flag and branch code disagree", "Conditional", "error", "B_04.01", "(none)", "ITS",
      "Give the branch code when the entity using the service is a branch; leave it empty otherwise."),
    R("DRV-20", "Hard to substitute, no reason given", "Conditional", "warning", "B_07.01", "v8825_m", "EBA",
      "Explain why the provider is not substitutable or only with high complexity."),
    R("DRV-21", "Critical function without reasons", "Conditional", "warning", "B_06.01", "(none)", "ITS",
      "State why the function is critical or important (DORA Art. 3 definition of a critical or important function)."),
    R("DRV-22", "Alternatives flagged but none identified", "Conditional", "warning", "B_07.01", "(none)", "custom",
      "Name the alternative providers, or set the flag to false."),
    R("DRV-23", "Data stored but no storage location", "Conditional", "error", "B_02.02", "(none)", "ITS",
      "Give the country of the data at rest, or set storage to false."),
    R("DRV-30", "Contract reference not found in B_02.01", "Referential integrity", "error", "B_02.02, B_03.01, B_03.02, B_04.01, B_05.02, B_07.01", "807", "EBA",
      "Fix the reference, or add the contract to B_02.01."),
    R("DRV-31", "Entity LEI not found in B_01.02", "Referential integrity", "error", "B_01.01, B_01.03, B_02.02, B_03.01, B_04.01, B_06.01", "807", "EBA",
      "Fix the LEI, or add the entity to B_01.02."),
    R("DRV-32", "Provider code not found in B_05.01", "Referential integrity", "error", "B_02.02, B_03.02, B_05.01, B_05.02, B_07.01", "807", "EBA",
      "Fix the code, or add the provider (or the sub-contractor, or the parent) to B_05.01."),
    R("DRV-33", "Function not found in B_06.01", "Referential integrity", "error", "B_02.02", "807", "EBA",
      "Fix the function identifier, or add the function to B_06.01."),
    R("DRV-34", "Assessment or supply chain row has no matching contract row", "Referential integrity", "error", "B_05.02, B_07.01", "807", "EBA",
      "The contract, provider and service type must exist together in B_02.02."),
    R("DRV-35", "Overarching reference does not point to a master agreement", "Referential integrity", "error", "B_02.01", "807", "EBA",
      "Point to a contract of type Overarching/master agreement that exists in B_02.01."),
    R("DRV-36", "Branch code not found in B_01.03", "Referential integrity", "error", "B_04.01", "807", "EBA",
      "Fix the branch code, or add the branch to B_01.03 under its head office."),
    R("DRV-40", "Contract missing from a template that must list it", "Cross-template", "error", "B_02.01", "(none)", "ITS",
      "Every contract needs rows in B_03.01 and B_03.02; contracts other than master agreements also in B_02.02 and B_04.01."),
    R("DRV-41", "Provider in B_02.02 is not the one in B_03.02", "Cross-template", "warning", "B_02.02", "(none)", "custom",
      "The provider that signs the contract (B_03.02) must be the provider of the service (B_02.02)."),
    R("DRV-42", "Provider is not used by any contract", "Cross-template", "warning", "B_05.01", "(none)", "custom",
      "Remove the provider, or add the contract that uses it. A provider that is only an ultimate parent is allowed."),
    R("DRV-43", "Assessment missing, or present for a non-critical function", "Cross-template", "warning", "B_02.02, B_07.01", "(none)", "ITS",
      "B_07.01 is completed for contracts supporting critical or important functions, and only for those."),
    R("DRV-44", "Level of reliance inconsistent with criticality", "Cross-template", "warning", "B_02.02", "(none)", "ITS",
      "Fill the level of reliance for services supporting a critical function, and leave it empty for the others."),
    R("DRV-45", "Critical, hard to substitute, and no exit plan", "Cross-template", "warning", "B_07.01", "(none)", "custom",
      "DORA Art. 28(8) expects an exit strategy for critical services. Confirm the plan exists or set it up."),
    R("DRV-46", "Provider total expense differs from the sum of its contracts", "Cross-template", "warning", "B_05.01", "(none)", "custom",
      "Reconcile B_05.01 total expense with the contract expenses in B_02.01 (same currency)."),
    R("DRV-47", "Supply chain is inconsistent", "Cross-template", "warning", "B_05.02", "(none)", "custom",
      "Ranks must run 1, 2, 3 without gaps, and a provider cannot be its own sub-contractor."),
]

RISK_FLAGS = [
    R("CON-01", "Provider group takes a large share of ICT spend", "Concentration", "info", "B_02.01, B_03.02, B_05.01", "(DORA Art. 29)", "custom",
      "Review the dependency and the exit options for this provider group."),
    R("CON-02", "Provider group supports many critical functions", "Concentration", "info", "B_02.02, B_06.01", "(DORA Art. 29)", "custom",
      "Check whether one outage could hit several critical functions at once."),
    R("CON-03", "High spend share under one non-EU jurisdiction", "Concentration", "info", "B_05.01", "(DORA Art. 29)", "custom",
      "Review the third-country dependency (ultimate parent country)."),
    R("CON-04", "Critical function depends on a single provider", "Concentration", "info", "B_02.02, B_06.01", "(DORA Art. 28(8))", "custom",
      "Document the alternative or the exit route for this function."),
]

BY_ID = {r.id: r for r in RULES + RISK_FLAGS}
SEVERITIES = ("error", "warning")
