"""The data model of the register: templates, columns, kinds, keys.

Column codes, labels, primary keys and nullability follow the EBA 'Data Model for DORA RoI' (April 2025).
`kind` is this project's tag for the check family a column belongs to.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Col:
    code: str
    label: str
    kind: str          # lei pid ptype country currency date dpast int money bool enum:<list> text id
    pk: bool = False
    required: bool = True
    type_col: Optional[str] = None   # for kind 'pid': the column that declares LEI or EUID


@dataclass(frozen=True)
class Template:
    code: str
    name: str
    cols: List[Col]

    @property
    def pk(self) -> List[str]:
        return [c.code for c in self.cols if c.pk]

    @property
    def codes(self) -> List[str]:
        return [c.code for c in self.cols]

    def col(self, code: str) -> Col:
        return next(c for c in self.cols if c.code == code)


def _t(code, name, *cols):
    return Template(code, name, list(cols))


C = Col
TEMPLATES: Dict[str, Template] = OrderedDict((t.code, t) for t in [
    _t("B_01.01", "Entity maintaining the register of information",
       C("c0010", "LEI of the entity maintaining the register", "lei", pk=True),
       C("c0020", "Name of the entity", "text"), C("c0030", "Country of the entity", "country"),
       C("c0040", "Type of entity", "enum:entity_type"), C("c0050", "Competent authority", "text"),
       C("c0060", "Reporting date", "date")),
    _t("B_01.02", "Entities within the scope of the register",
       C("c0010", "LEI of the entity", "lei", pk=True), C("c0020", "Name of the entity", "text"),
       C("c0030", "Country of the entity", "country"), C("c0040", "Type of entity", "enum:entity_type"),
       C("c0050", "Hierarchy of the entity within the group", "enum:hierarchy"),
       C("c0060", "LEI of the direct parent undertaking", "lei", required=False),
       C("c0070", "Date of last update", "dpast"), C("c0080", "Date of integration in the register", "dpast"),
       C("c0090", "Date of deletion from the register", "date", required=False),
       C("c0100", "Currency", "currency", required=False),
       C("c0110", "Value of total assets", "money", required=False)),
    _t("B_01.03", "Branches",
       C("c0010", "Identification code of the branch", "id", pk=True),
       C("c0020", "LEI of the financial entity head office of the branch", "lei", pk=True),
       C("c0030", "Name of the branch", "text"), C("c0040", "Country of the branch", "country")),
    _t("B_02.01", "Contractual arrangements: general information",
       C("c0010", "Contractual arrangement reference number", "id", pk=True),
       C("c0020", "Type of contractual arrangement", "enum:arrangement_type"),
       C("c0030", "Overarching contractual arrangement reference number", "id", required=False),
       C("c0040", "Currency of the amount reported", "currency"),
       C("c0050", "Annual expense or estimated cost for the past year", "money")),
    _t("B_02.02", "Contractual arrangements: specific information",
       C("c0010", "Contractual arrangement reference number", "id", pk=True),
       C("c0020", "LEI of the financial entity making use of the ICT service", "lei", pk=True),
       C("c0030", "Identification code of the ICT third-party service provider", "pid", pk=True, type_col="c0040"),
       C("c0040", "Type of code to identify the provider", "ptype", required=False),
       C("c0050", "Function identifier", "id", pk=True),
       C("c0060", "Type of ICT services", "enum:service_type", pk=True),
       C("c0070", "Start date of the contractual arrangement", "date"),
       C("c0080", "End date of the contractual arrangement", "date", required=False),
       C("c0090", "Reason of the termination or ending", "enum:termination_reason", required=False),
       C("c0100", "Notice period for the financial entity (days)", "int", required=False),
       C("c0110", "Notice period for the ICT third-party service provider (days)", "int", required=False),
       C("c0120", "Country of the governing law", "country", required=False),
       C("c0130", "Country of provision of the ICT services", "country", pk=True),
       C("c0140", "Storage of data", "bool"),
       C("c0150", "Location of the data at rest (storage)", "country", pk=True, required=False),
       C("c0160", "Location of management of the data (processing)", "country", pk=True),
       C("c0170", "Sensitiveness of the data stored", "enum:sensitivity", required=False),
       C("c0180", "Level of reliance on the ICT service supporting the critical or important function",
         "enum:reliance", required=False)),
    _t("B_03.01", "Entities signing the arrangements (receiving ICT services)",
       C("c0010", "Contractual arrangement reference number", "id", pk=True),
       C("c0020", "LEI of the entity signing the contractual arrangement", "lei", pk=True)),
    _t("B_03.02", "Providers signing the arrangements",
       C("c0010", "Contractual arrangement reference number", "id", pk=True),
       C("c0020", "Identification code of the ICT third-party service provider", "pid", pk=True, type_col="c0030"),
       C("c0030", "Type of code of the provider", "ptype", required=False)),
    _t("B_04.01", "Financial entities making use of the ICT services",
       C("c0010", "Contractual arrangement reference number", "id", pk=True),
       C("c0020", "LEI of the financial entity", "lei", pk=True),
       C("c0030", "Is the entity making use of the ICT services a branch?", "bool"),
       C("c0040", "Identification code of the branch", "id", pk=True, required=False)),
    _t("B_05.01", "ICT third-party service providers",
       C("c0010", "Identification code of the provider", "pid", pk=True, type_col="c0020"),
       C("c0020", "Type of code to identify the provider", "ptype"),
       C("c0030", "Additional identification code", "id", required=False),
       C("c0040", "Type of additional identification code", "text", required=False),
       C("c0050", "Legal name of the provider", "text"),
       C("c0060", "Name of the provider in Latin alphabet", "text", required=False),
       C("c0070", "Type of person of the provider", "enum:person_type"),
       C("c0080", "Country of the provider's headquarters", "country"),
       C("c0090", "Currency of the amount reported", "currency", required=False),
       C("c0100", "Total annual expense or estimated cost of the provider", "money", required=False),
       C("c0110", "Identification code of the provider's ultimate parent undertaking", "pid", required=False,
         type_col="c0120"),
       C("c0120", "Type of code of the ultimate parent undertaking", "ptype", required=False)),
    _t("B_05.02", "ICT service supply chains",
       C("c0010", "Contractual arrangement reference number", "id", pk=True),
       C("c0020", "Type of ICT services", "enum:service_type", pk=True),
       C("c0030", "Identification code of the ICT third-party service provider", "pid", pk=True, type_col="c0040"),
       C("c0040", "Type of code of the provider", "ptype", required=False),
       C("c0050", "Rank", "int", pk=True),
       C("c0060", "Identification code of the recipient of sub-contracted ICT services", "pid", pk=True,
         type_col="c0070"),
       C("c0070", "Type of code of the recipient", "ptype", required=False)),
    _t("B_06.01", "Functions identification",
       C("c0010", "Function identifier", "id", pk=True), C("c0020", "Licenced activity", "text"),
       C("c0030", "Function name", "text"), C("c0040", "LEI of the financial entity", "lei", pk=True),
       C("c0050", "Criticality or importance assessment", "enum:yes_no"),
       C("c0060", "Reasons for criticality or importance", "text", required=False),
       C("c0070", "Date of the last assessment of criticality or importance", "dpast"),
       C("c0080", "Recovery time objective of the function (hours)", "int"),
       C("c0090", "Recovery point objective of the function (hours)", "int"),
       C("c0100", "Impact of discontinuing the function", "enum:impact")),
    _t("B_07.01", "Assessment of the ICT services",
       C("c0010", "Contractual arrangement reference number", "id", pk=True),
       C("c0020", "Identification code of the ICT third-party service provider", "pid", pk=True, type_col="c0030"),
       C("c0030", "Type of code of the provider", "ptype", required=False),
       C("c0040", "Type of ICT services", "enum:service_type", pk=True),
       C("c0050", "Substitutability of the ICT third-party service provider", "enum:substitutability"),
       C("c0060", "Reason if not substitutable or difficult to substitute", "text", required=False),
       C("c0070", "Date of the last audit on the provider", "dpast"),
       C("c0080", "Existence of an exit plan", "bool"),
       C("c0090", "Possibility of reintegration of the contracted ICT service", "enum:reintegration"),
       C("c0100", "Impact of discontinuing the ICT services", "enum:impact"),
       C("c0110", "Are there alternative ICT third-party service providers identified?", "bool"),
       C("c0120", "Identification of alternative ICT third-party service providers", "text", required=False)),
])
