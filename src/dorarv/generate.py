"""Synthetic register generator and defect injector.

Everything here is invented: group, entities, providers, contracts, amounts. LEIs are generated with valid ISO 17442
check digits and a fixed 'SYNT' prefix; they are not registered with any LOU. The clean register is built so that the
validator reports nothing. `inject` then plants known defects and writes the answer key.
"""
from __future__ import annotations

import json
import random
from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from . import lei as leimod
from .model import TEMPLATES
from .reference import ROOT

SEED = 2025
REPORTING_DATE = "2025-12-31"
OUT = ROOT / "data" / "synthetic"
GROUP = "Meridian Beispielbank Group (SYNTHETIC)"

# name, country, type, hierarchy, total assets (EUR)
ENTITIES = [
    ("Meridian Beispielbank AG", "DE", "Credit institution", "Parent undertaking", 48_200_000_000),
    ("Meridian Wertpapier GmbH", "DE", "Investment firm", "Subsidiary", 3_100_000_000),
    ("Meridian Payments S.A.", "LU", "Payment institution", "Subsidiary", 1_450_000_000),
    ("Meridian Digital Assets GmbH", "DE", "Crypto-asset service provider", "Subsidiary", 620_000_000),
    ("Meridian Versicherung AG", "DE", "Insurance undertaking", "Subsidiary", 9_700_000_000),
    ("Meridian Leasing GmbH", "DE", "Credit institution", "Subsidiary", 2_050_000_000),
    ("Meridian Bausparkasse AG", "DE", "Credit institution", "Subsidiary", 6_400_000_000),
    ("Meridian Asset Management S.A.", "LU", "Investment firm", "Subsidiary", 410_000_000),
    ("Meridian Zahlungsdienste GmbH", "DE", "Payment institution", "Subsidiary", 280_000_000),
    ("Meridian Lebensversicherung AG", "DE", "Insurance undertaking", "Subsidiary", 12_300_000_000),
    ("Meridian Consumer Finance S.A.", "FR", "Credit institution", "Subsidiary", 1_900_000_000),
    ("Meridian Brokerage Ltd", "IE", "Investment firm", "Subsidiary", 150_000_000),
    ("Meridian Custody Services S.A.", "LU", "Investment firm", "Subsidiary", 330_000_000),
    ("Meridian Rückversicherung AG", "DE", "Insurance undertaking", "Subsidiary", 4_600_000_000),
]
BRANCHES = [("BR-E1-FR01", 0, "Meridian Beispielbank, Paris branch", "FR"),
            ("BR-E1-ES01", 0, "Meridian Beispielbank, Madrid branch", "ES"),
            ("BR-E3-IT01", 2, "Meridian Payments, Milan branch", "IT")]

# name, HQ country, code type, ultimate parent index (None = itself), contract currency
PROVIDERS = [
    ("Aurelia Cloud Services Ltd", "IE", "LEI", 22, "EUR"), ("Borealis Compute GmbH", "DE", "LEI", None, "EUR"),
    ("Cobalt Data Platforms Inc.", "US", "LEI", 23, "USD"), ("Delphi Core Banking Software AG", "DE", "LEI", None, "EUR"),
    ("Eskarina Payments Gateway B.V.", "NL", "LEI", None, "EUR"), ("Fjord Network Carrier AS", "NO", "LEI", None, "EUR"),
    ("Gantry Security Operations S.A.S.", "FR", "LEI", None, "EUR"), ("Helvetia Hosting AG", "CH", "LEI", None, "EUR"),
    ("Ionic Market Data Ltd", "GB", "LEI", None, "GBP"), ("Juniper Service Desk Pvt Ltd", "IN", "LEI", None, "EUR"),
    ("Kestrel Analytics GmbH", "DE", "LEI", None, "EUR"), ("Lumen Telecom S.p.A.", "IT", "LEI", None, "EUR"),
    ("Marlowe Consulting LLP", "GB", "LEI", None, "EUR"), ("Nimbus CRM Inc.", "US", "LEI", 23, "USD"),
    ("Orchid Document Archive Sp. z o.o.", "PL", "EUID", None, "EUR"), ("Pylon Hardware Leasing GmbH", "DE", "EUID", None, "EUR"),
    ("Quasar Trading Platform Pte Ltd", "SG", "LEI", None, "USD"), ("Rowan Identity Services Oy", "FI", "LEI", None, "EUR"),
    ("Sable Backup & Recovery B.V.", "NL", "LEI", None, "EUR"), ("Tessera Regulatory Reporting AG", "AT", "LEI", None, "EUR"),
    ("Umbra Threat Intelligence Ltd", "IL", "LEI", None, "EUR"), ("Vantage Custody Technologies GmbH", "DE", "LEI", None, "EUR"),
    ("Aurelia Holdings Inc.", "US", "LEI", None, "EUR"), ("Cobalt Group Holdings LLC", "US", "LEI", None, "EUR"),
]
MASTER_PROVIDERS = {0: "RC-M001", 3: "RC-M002", 2: "RC-M003"}   # providers that have a master agreement
HARD = {0: "Highly complex substitutability", 3: "Not substitutable", 4: "Highly complex substitutability",
        2: "Highly complex substitutability", 21: "Not substitutable"}
MEDIUM = {16, 8, 6, 7, 13, 17}

S = {k: v for k, v in zip("abcdefghijklmno", [
    "Cloud services: IaaS", "Cloud services: PaaS", "Cloud services: SaaS",
    "ICT, facilities and hosting services (excluding Cloud services)", "Software licencing (excluding SaaS)",
    "ICT operation management (including maintenance)", "ICT security management services", "Provision of data",
    "Data analysis", "Non-Cloud Data storage", "Telecommunication carrier", "Network Infrastructure",
    "Hardware and physical devices", "ICT help desk and first level support", "ICT Consulting"])}
STORES = {S["a"], S["b"], S["c"], S["d"], S["j"]}
CLOUD = {S["a"], S["b"], S["c"]}

# function id, entity index, name, licensed activity, critical, [(provider, service, annual spend in contract currency)]
FUNCTIONS = [
    ("F0101", 0, "Core banking and ledger", "Deposit-taking and lending", True, [(3, S["e"], 2_400_000), (1, S["d"], 1_900_000)]),
    ("F0102", 0, "Online and mobile banking", "Deposit-taking and lending", True, [(0, S["a"], 5_200_000), (17, S["g"], 420_000)]),
    ("F0103", 0, "Payments processing", "Payment services", True, [(4, S["f"], 1_250_000), (0, S["b"], 1_600_000)]),
    ("F0104", 0, "Regulatory reporting", "Deposit-taking and lending", False, [(19, S["c"], 380_000)]),
    ("F0105", 0, "HR and payroll", "Deposit-taking and lending", False, [(13, S["c"], 210_000)]),
    ("F0106", 0, "Document archive", "Deposit-taking and lending", False, [(14, S["j"], 150_000)]),
    ("F0107", 0, "IT service desk", "Deposit-taking and lending", False, [(9, S["n"], 520_000), (15, S["m"], 300_000)]),
    ("F0108", 0, "Network and connectivity", "Deposit-taking and lending", True, [(5, S["k"], 640_000), (11, S["l"], 580_000)]),
    ("F0109", 0, "Security operations centre", "Deposit-taking and lending", True, [(6, S["g"], 700_000)]),
    ("F0201", 1, "Securities order routing", "Investment services", True, [(16, S["c"], 980_000), (0, S["a"], 1_400_000)]),
    ("F0202", 1, "Market data", "Investment services", True, [(8, S["h"], 840_000)]),
    ("F0203", 1, "Settlement back office", "Investment services", True, [(3, S["e"], 610_000)]),
    ("F0204", 1, "Client reporting", "Investment services", False, [(10, S["i"], 190_000), (13, S["c"], 120_000)]),
    ("F0301", 2, "Card and SEPA processing", "Payment services", True, [(4, S["f"], 1_050_000), (2, S["b"], 870_000)]),
    ("F0302", 2, "AML screening", "Payment services", True, [(10, S["i"], 460_000), (20, S["h"], 310_000)]),
    ("F0303", 2, "Customer onboarding (eKYC)", "Payment services", False, [(17, S["c"], 280_000)]),
    ("F0401", 3, "Crypto-asset custody", "Custody of crypto-assets", True, [(21, S["f"], 1_150_000), (0, S["a"], 1_200_000)]),
    ("F0402", 3, "Trading engine", "Exchange of crypto-assets", True, [(2, S["b"], 1_300_000), (16, S["c"], 520_000)]),
    ("F0403", 3, "On-chain monitoring", "Custody of crypto-assets", False, [(20, S["h"], 240_000)]),
    ("F0501", 4, "Policy administration", "Insurance underwriting", True, [(3, S["e"], 770_000), (7, S["d"], 640_000)]),
    ("F0502", 4, "Claims handling", "Insurance underwriting", True, [(13, S["c"], 430_000), (18, S["j"], 260_000)]),
    ("F0503", 4, "Actuarial analytics", "Insurance underwriting", False, [(10, S["i"], 350_000), (12, S["o"], 160_000)]),
]
TWO_ROWS = {("F0106", 14), ("F0503", 10)}   # contracts reported in two countries of provision (non-critical ones)
CHAINS = [("F0101", 3, [0, 18]), ("F0103", 4, [1]), ("F0201", 16, [0]), ("F0402", 2, [0, 18]),
          ("F0401", 21, [7]), ("F0502", 13, [2])]
BRANCH_USE = {"F0108": "BR-E1-FR01", "F0107": "BR-E1-ES01"}
REASONS = ["Failure would stop a core regulated service", "Supports a service with a recovery time of a few hours",
           "Required to meet payment, settlement or custody obligations", "Customer-facing service of a licensed activity"]
Tables = Dict[str, pd.DataFrame]


def _d(rng: random.Random, a: date, b: date) -> str:
    return (a + timedelta(days=rng.randint(0, (b - a).days))).isoformat()


def _frame(code: str, rows: List[list]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=TEMPLATES[code].codes, dtype=str).fillna("")


def build_clean(seed: int = SEED) -> Tables:
    rng = random.Random(seed)
    ent = [leimod.make_lei(rng, "SYNT") for _ in ENTITIES]
    pid, ptype = [], []
    for i, (name, cc, ct, _, _) in enumerate(PROVIDERS):
        if ct == "LEI":
            pid.append(leimod.make_lei(rng, "SYNT")); ptype.append("LEI")
        else:
            pid.append(f"{cc}SYN{i:03d}.HRB9{i:05d}"); ptype.append("EUID")

    # contracts -------------------------------------------------------------------------------------------------
    contracts = []   # dicts
    n = 0
    for fid, e, fname, _, crit, lines in FUNCTIONS:
        for prov, service, spend in lines:
            n += 1
            contracts.append(dict(ref=f"RC-{n:04d}", fid=fid, ent=e, prov=prov, service=service, spend=spend, crit=crit,
                                  two=(fid, prov) in TWO_ROWS,
                                  start=_d(rng, date(2018, 1, 1), date(2024, 6, 30)),
                                  end=_d(rng, date(2026, 3, 1), date(2028, 12, 31)) if n % 8 == 0 else "",
                                  master=MASTER_PROVIDERS.get(prov, "")))
    masters = [dict(ref=ref, prov=p) for p, ref in MASTER_PROVIDERS.items()]
    by_fp = {(c["fid"], c["prov"]): c for c in contracts}

    t: Tables = OrderedDict()
    t["B_01.01"] = _frame("B_01.01", [[ent[0], ENTITIES[0][0], "DE", ENTITIES[0][2], "BaFin", REPORTING_DATE]])
    t["B_01.02"] = _frame("B_01.02", [
        [ent[i], nm, cc, ty, hi, ent[0] if i else "", "2025-12-15", "2025-01-01", "", "EUR", str(ta)]
        for i, (nm, cc, ty, hi, ta) in enumerate(ENTITIES)])
    t["B_01.03"] = _frame("B_01.03", [[b, ent[e], nm, cc] for b, e, nm, cc in BRANCHES])

    r201, r202, r301, r302, r401 = [], [], [], [], []
    for m in masters:
        r201.append([m["ref"], "Overarching/master agreement", "", PROVIDERS[m["prov"]][4], "0"])
        r301.append([m["ref"], ent[0]]); r302.append([m["ref"], pid[m["prov"]], ptype[m["prov"]]])
    for c in contracts:
        typ = "Subsequent or associated arrangement" if c["master"] else "Standalone arrangement"
        r201.append([c["ref"], typ, c["master"], PROVIDERS[c["prov"]][4], str(c["spend"])])
        r301.append([c["ref"], ent[c["ent"]]]); r302.append([c["ref"], pid[c["prov"]], ptype[c["prov"]]])
        br = BRANCH_USE.get(c["fid"], "") if c["ent"] == 0 else ""
        r401.append([c["ref"], ent[c["ent"]], "true" if br else "false", br])
        hq = PROVIDERS[c["prov"]][1]
        storing = c["service"] in STORES
        places = [("IE" if c["service"] in CLOUD else hq if hq in ("DE", "NL", "FR", "IT", "PL", "AT", "FI") else "DE")]
        if c["two"]:
            places.append("DE" if places[0] != "DE" else "NL")
        hard = c["prov"] in HARD
        rely = ("Full reliance" if hard else "High reliance" if c["prov"] in MEDIUM or c["spend"] > 700_000 else "Medium reliance")
        for place in places:
            r202.append([c["ref"], ent[c["ent"]], pid[c["prov"]], ptype[c["prov"]], c["fid"], c["service"], c["start"],
                         c["end"], "", str(rng.choice([30, 60, 90, 180])), str(rng.choice([90, 180, 365])),
                         "US" if hq == "US" else "DE", place, "true" if storing else "false",
                         place if storing else "", place,
                         ("High" if c["crit"] else "Moderate") if storing else "", rely if c["crit"] else ""])
    t["B_02.01"] = _frame("B_02.01", r201)
    t["B_02.02"] = _frame("B_02.02", r202)
    t["B_03.01"] = _frame("B_03.01", r301)
    t["B_03.02"] = _frame("B_03.02", r302)
    t["B_04.01"] = _frame("B_04.01", r401)

    # providers ---------------------------------------------------------------------------------------------------
    totals: Dict[int, int] = {}
    for c in contracts:
        totals[c["prov"]] = totals.get(c["prov"], 0) + c["spend"]
    r501 = []
    for i, (name, cc, ct, par, ccy) in enumerate(PROVIDERS):
        parent = i if par is None else par
        used = i in totals
        r501.append([pid[i], ptype[i], "", "", name, "", "Legal person", cc, ccy if used else "",
                     str(totals[i]) if used else "", pid[parent], ptype[parent]])
    t["B_05.01"] = _frame("B_05.01", r501)

    r502 = []
    for fid, prov, subs in CHAINS:
        c = by_fp[(fid, prov)]
        for rank, s in enumerate(subs, 1):
            r502.append([c["ref"], c["service"], pid[prov], ptype[prov], str(rank), pid[s], ptype[s]])
    t["B_05.02"] = _frame("B_05.02", r502)

    # functions and assessments -----------------------------------------------------------------------------------
    r601 = []
    for k, (fid, e, fname, lic, crit, _) in enumerate(FUNCTIONS):
        r601.append([fid, lic, fname, ent[e], "Yes" if crit else "No", REASONS[k % len(REASONS)] if crit else "",
                     _d(rng, date(2025, 3, 1), date(2025, 11, 30)),
                     str(rng.choice([2, 4, 6, 8]) if crit else rng.choice([24, 48, 72])),
                     str(rng.choice([0, 1, 4]) if crit else rng.choice([24, 48])), "High" if crit else rng.choice(["Low", "Medium"])])
    t["B_06.01"] = _frame("B_06.01", r601)

    r701 = []
    for c in contracts:
        if not c["crit"]:
            continue
        p = c["prov"]
        sub = HARD.get(p, "Medium complexity" if p in MEDIUM else "Low complexity" if p not in (18,) else "Easily substitutable")
        hard = p in HARD
        r701.append([c["ref"], pid[p], ptype[p], c["service"], sub,
                     "Provider operates the system of record; migration would take well over a year" if hard else "",
                     _d(rng, date(2025, 2, 1), date(2025, 11, 30)),
                     "true" if hard or rng.random() < 0.7 else "false",
                     "Highly complex" if sub == "Not substitutable" else "Difficult" if hard else "Easy",
                     "High" if hard else rng.choice(["Medium", "High"]),
                     "false" if hard else "true", "" if hard else "Second source assessed in the exit plan"])
    t["B_07.01"] = _frame("B_07.01", r701)
    return t


def write_register(tables: Tables, folder: Path, notice: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for code, df in tables.items():
        df[TEMPLATES[code].codes].to_csv(folder / f"{code}.csv", index=False)
    (folder / "MANIFEST.json").write_text(json.dumps(
        {"synthetic": True, "group": GROUP, "reporting_date": REPORTING_DATE, "seed": SEED, "notice": notice,
         "templates": {c: len(df) for c, df in tables.items()}}, indent=2) + "\n")


# ---------------------------------------------------------------------------------------------------------------------
# Defect injection
# ---------------------------------------------------------------------------------------------------------------------
class Injector:
    def __init__(self, tables: Tables, seed: int):
        self.t = {k: v.copy() for k, v in tables.items()}
        self.rng = random.Random(seed + 1)
        self.used: Dict[str, set] = {}
        self.key: List[dict] = []
        self.n = 0
        self.synth = [leimod.make_lei(self.rng, "SYNT") for _ in range(12)]   # valid, unregistered, not in the register

    # helpers
    def pick(self, code: str, mask=None) -> int:
        df = self.t[code]
        ok = [i for i in df.index[mask] if i not in self.used.setdefault(code, set())] if mask is not None else \
            [i for i in df.index if i not in self.used.setdefault(code, set())]
        assert ok, f"no free row in {code}"
        i = self.rng.choice(ok)
        self.used[code].add(i)
        return i

    def append(self, code: str, row) -> int:
        df = self.t[code]
        df.loc[len(df)] = row
        self.used.setdefault(code, set()).add(len(df) - 1)
        return len(df) - 1

    def new(self, text: str, detectable: bool = True) -> str:
        self.n += 1
        self._id, self._text, self._det = f"D{self.n:02d}", text, detectable
        return self._id

    def exp(self, rule: str, code: str, idx: int, col: str = "") -> None:
        self.key.append(dict(defect_id=self._id, defect=self._text, rule_id=rule if self._det else "(none)", template=code,
                             row=int(idx) + 2, column=col, detectable=self._det))

    def set(self, code: str, idx: int, col: str, val: str) -> None:
        self.t[code].at[idx, col] = val

    def get(self, code: str, idx: int, col: str) -> str:
        return self.t[code].at[idx, col]

    def prov_row(self, provider_id: str) -> int:
        return int(self.t["B_05.01"].index[self.t["B_05.01"]["c0010"] == provider_id][0])

    def contract_provider(self, ref: str) -> str:
        d = self.t["B_03.02"]
        return d.loc[d["c0010"] == ref, "c0020"].iloc[0]


def inject(tables: Tables, seed: int = SEED) -> Tuple[Tables, pd.DataFrame]:
    X = Injector(tables, seed)
    t = X.t
    crit_fn = set(t["B_06.01"].loc[t["B_06.01"]["c0050"] == "Yes", "c0010"])
    recon_used: set = set()      # provider rows whose spend reconciliation is already used by a defect
    pid_of = list(t["B_05.01"]["c0010"])
    ref_of = {}
    for _, r in t["B_02.02"].iterrows():
        ref_of[(r["c0050"], pid_of.index(r["c0030"]))] = r["c0010"]

    d22 = t["B_02.02"]
    reserved = {  # rows that specific defects need; random picks must leave them alone
        "orchid": int(d22.index[(d22["c0050"] == "F0106") & (d22["c0130"] == "DE")][0]),
        "kestrel": int(d22.index[(d22["c0050"] == "F0503") & (d22["c0030"] == pid_of[10]) & (d22["c0130"] == "NL")][0])}
    X.used.setdefault("B_02.02", set()).update(reserved.values())

    def free():
        """Provider rows not yet used for a currency / total-expense defect."""
        return ~pd.Series(t["B_05.01"].index.isin(recon_used), index=t["B_05.01"].index)

    def contracts_of_unused_provider(mask_fn=None):
        d = t["B_02.01"]
        prov_of = t["B_03.02"].drop_duplicates("c0010").set_index("c0010")["c0020"]
        for i in d.index:
            if i in X.used.get("B_02.01", set()) or d.at[i, "c0020"] == "Overarching/master agreement":
                continue
            pr = X.prov_row(prov_of[d.at[i, "c0010"]])
            if pr in recon_used or (mask_fn and not mask_fn(i)):
                continue
            return i, pr
        raise AssertionError("no contract")

    def single_provider_contract():
        """A contract whose provider has exactly one contract (for the order-of-magnitude defect)."""
        cnt = t["B_03.02"].drop_duplicates(["c0010", "c0020"]).groupby("c0020").size()
        d = t["B_02.01"]
        prov_of = t["B_03.02"].drop_duplicates("c0010").set_index("c0010")["c0020"]
        for i in d.index:
            p = prov_of.get(d.at[i, "c0010"])
            if p is not None and cnt.get(p, 0) == 1 and d.at[i, "c0020"] != "Overarching/master agreement":
                pr = X.prov_row(p)
                if pr not in recon_used:
                    return i, pr
        raise AssertionError("none")

    # ---- defects the validator cannot see by design (listed first: one of them deletes rows) --------------------------
    X.new("A critical function was marked non-critical and its assessment removed (a consistent but wrong judgement)", False)
    fi = X.pick("B_06.01", t["B_06.01"]["c0030"] == "Market data")
    fid = X.get("B_06.01", fi, "c0010")
    X.set("B_06.01", fi, "c0050", "No"); X.set("B_06.01", fi, "c0060", "")
    for i in t["B_02.02"].index[t["B_02.02"]["c0050"] == fid]:
        X.set("B_02.02", i, "c0180", "")
        X.used.setdefault("B_02.02", set()).add(i)
    refs = set(t["B_02.02"].loc[t["B_02.02"]["c0050"] == fid, "c0010"])
    gone = t["B_07.01"].index[t["B_07.01"]["c0010"].isin(refs)]
    t["B_07.01"] = t["B_07.01"].drop(gone).reset_index(drop=True)
    X.used["B_07.01"] = set()
    X.exp("(none)", "B_06.01", fi, "c0050")
    crit_fn.discard(fid)

    X.new("Parent LEI is well-formed and has valid check digits but belongs to an unrelated entity", False)
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0060", X.synth[0]); X.exp("(none)", "B_01.02", i, "c0060")

    X.new("Contract expense is ten times too high in both B_02.01 and the provider total (internally consistent)", False)
    k, pr = single_provider_contract()
    X.used.setdefault("B_02.01", set()).add(k); recon_used.add(pr); X.used.setdefault("B_05.01", set()).add(pr)
    old = int(X.get("B_02.01", k, "c0050")); X.set("B_02.01", k, "c0050", str(old * 10))
    X.set("B_05.01", pr, "c0100", str(int(X.get("B_05.01", pr, "c0100")) + 9 * old)); X.exp("(none)", "B_02.01", k, "c0050")

    X.new("Governing-law country is wrong (DE instead of US) but a valid code", False)
    i = X.pick("B_02.02", t["B_02.02"]["c0120"] == "US"); X.set("B_02.02", i, "c0120", "DE"); X.exp("(none)", "B_02.02", i, "c0120")

    # ---- completeness -------------------------------------------------------------------------------------------------
    X.new("Legal name of a provider is blank")
    i = X.pick("B_05.01", t["B_05.01"]["c0050"] != ""); X.set("B_05.01", i, "c0050", ""); X.exp("DRV-02", "B_05.01", i, "c0050")
    X.new("Start date of a contract is blank")
    i = X.pick("B_02.02"); X.set("B_02.02", i, "c0070", ""); X.exp("DRV-02", "B_02.02", i, "c0070")
    X.new("Function name is blank")
    i = X.pick("B_06.01"); X.set("B_06.01", i, "c0030", ""); X.exp("DRV-02", "B_06.01", i, "c0030")
    X.new("Country of a group entity is blank")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0030", ""); X.exp("DRV-02", "B_01.02", i, "c0030")
    X.new("Currency of a contract is blank")
    k, pr = contracts_of_unused_provider(); X.used.setdefault("B_02.01", set()).add(k); recon_used.add(pr)
    X.used.setdefault("B_05.01", set()).add(pr)
    X.set("B_02.01", k, "c0040", ""); X.exp("DRV-02", "B_02.01", k, "c0040")

    X.new("A branch is listed twice")
    i = X.pick("B_01.03"); j = X.append("B_01.03", t["B_01.03"].loc[i])
    X.exp("DRV-03", "B_01.03", i, "c0010"); X.exp("DRV-03", "B_01.03", j, "c0010")
    X.new("A contract-provider pair is listed twice in B_03.02")
    i = X.pick("B_03.02"); j = X.append("B_03.02", t["B_03.02"].loc[i])
    X.exp("DRV-03", "B_03.02", i, "c0010"); X.exp("DRV-03", "B_03.02", j, "c0010")

    # ---- formats ------------------------------------------------------------------------------------------------------
    X.new("Parent LEI typed in lower case")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0060", X.get("B_01.02", i, "c0060").lower())
    X.exp("DRV-04", "B_01.02", i, "c0060")
    X.new("Parent LEI has wrong check digits")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); v = X.get("B_01.02", i, "c0060")
    X.set("B_01.02", i, "c0060", v[:18] + f"{(int(v[18:]) + 1) % 100:02d}"); X.exp("DRV-05", "B_01.02", i, "c0060")
    X.new("LEI of the entity maintaining the register is one character short")
    X.set("B_01.01", 0, "c0010", X.get("B_01.01", 0, "c0010")[:19]); X.exp("DRV-04", "B_01.01", 0, "c0010"); X.exp("DRV-31", "B_01.01", 0, "c0010")
    X.new("Two characters of an entity LEI are transposed in B_02.02")
    i = X.pick("B_02.02", t["B_02.02"]["c0010"].str.startswith("RC-")); v = X.get("B_02.02", i, "c0020")
    for p in range(5, 15):
        w = v[:p] + v[p + 1] + v[p] + v[p + 2:]
        if w != v and not leimod.has_valid_checksum(w):
            break
    X.set("B_02.02", i, "c0020", w); X.exp("DRV-05", "B_02.02", i, "c0020"); X.exp("DRV-31", "B_02.02", i, "c0020")
    X.new("Signing-entity LEI typed in lower case in B_03.01")
    i = X.pick("B_03.01", t["B_03.01"]["c0010"].str.match(r"RC-\d")); X.set("B_03.01", i, "c0020", X.get("B_03.01", i, "c0020").lower())
    X.exp("DRV-04", "B_03.01", i, "c0020"); X.exp("DRV-31", "B_03.01", i, "c0020")
    X.new("Provider declared as EUID but the code is an LEI")
    i = X.pick("B_05.01", (t["B_05.01"]["c0020"] == "LEI") & (t["B_05.01"]["c0110"] == t["B_05.01"]["c0010"]) & (t["B_05.01"]["c0100"] != "")); X.set("B_05.01", i, "c0020", "EUID")
    X.exp("DRV-08", "B_05.01", i, "c0010")
    X.new("Provider declared as EUID in B_02.02 but the code is an LEI")
    i = X.pick("B_02.02", t["B_02.02"]["c0040"] == "LEI"); X.set("B_02.02", i, "c0040", "EUID"); X.exp("DRV-08", "B_02.02", i, "c0030")
    X.new("Country 'UK' instead of GB")
    i = X.pick("B_05.01", t["B_05.01"]["c0080"] == "GB"); X.set("B_05.01", i, "c0080", "UK"); X.exp("DRV-06", "B_05.01", i, "c0080")
    X.new("Country of provision 'XX'")
    i = X.pick("B_02.02", t["B_02.02"]["c0010"].map(t["B_02.02"]["c0010"].value_counts()) == 1)
    X.set("B_02.02", i, "c0130", "XX"); X.exp("DRV-06", "B_02.02", i, "c0130")
    X.new("Branch country as three letters")
    i = X.pick("B_01.03"); X.set("B_01.03", i, "c0040", "DEU"); X.exp("DRV-06", "B_01.03", i, "c0040")
    X.new("Currency 'EURO'")
    i = X.pick("B_01.02", t["B_01.02"]["c0100"] != ""); X.set("B_01.02", i, "c0100", "EURO"); X.exp("DRV-07", "B_01.02", i, "c0100")
    X.new("Currency 'US$' on a provider")
    i = X.pick("B_05.01", (t["B_05.01"]["c0090"] == "USD") & free()); recon_used.add(i); X.set("B_05.01", i, "c0090", "US$")
    X.exp("DRV-07", "B_05.01", i, "c0090")
    X.new("Entity type 'Bank' is not in the list")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0040", "Bank"); X.exp("DRV-09", "B_01.02", i, "c0040")
    X.new("Type of person 'Company' is not in the list")
    i = X.pick("B_05.01", t["B_05.01"]["c0050"] != ""); X.set("B_05.01", i, "c0070", "Company"); X.exp("DRV-09", "B_05.01", i, "c0070")
    X.new("Reintegration answer 'Maybe'")
    i = X.pick("B_07.01"); X.set("B_07.01", i, "c0090", "Maybe"); X.exp("DRV-09", "B_07.01", i, "c0090")
    X.new("Level of reliance 'Very high' is not in the list")
    i = X.pick("B_02.02", t["B_02.02"]["c0180"] != ""); X.set("B_02.02", i, "c0180", "Very high"); X.exp("DRV-09", "B_02.02", i, "c0180")
    X.new("Storage flag typed as 'yes'")
    i = X.pick("B_02.02", t["B_02.02"]["c0140"] == "false"); X.set("B_02.02", i, "c0140", "yes"); X.exp("DRV-09", "B_02.02", i, "c0140")
    X.new("End date typed as dd/mm/yyyy")
    i = X.pick("B_02.02", t["B_02.02"]["c0080"] != ""); X.set("B_02.02", i, "c0080", "31/03/2030"); X.exp("DRV-10", "B_02.02", i, "c0080")
    X.new("Assessment date 30 February")
    i = X.pick("B_06.01"); X.set("B_06.01", i, "c0070", "2025-02-30"); X.exp("DRV-10", "B_06.01", i, "c0070")
    X.new("Audit date in month 13")
    i = X.pick("B_07.01"); X.set("B_07.01", i, "c0070", "2025-13-01"); X.exp("DRV-10", "B_07.01", i, "c0070")
    X.new("Recovery time objective written in words")
    i = X.pick("B_06.01"); X.set("B_06.01", i, "c0080", "four hours"); X.exp("DRV-11", "B_06.01", i, "c0080")
    X.new("Notice period written with a unit")
    i = X.pick("B_02.02"); X.set("B_02.02", i, "c0100", "30 days"); X.exp("DRV-11", "B_02.02", i, "c0100")
    X.new("Total assets 'n/a'")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0110", "n/a"); X.exp("DRV-11", "B_01.02", i, "c0110")
    X.new("Rank written in words")
    i = X.pick("B_05.02", (t["B_05.02"]["c0050"] == "2") & (t["B_05.02"]["c0010"] == ref_of[("F0402", 2)])); X.set("B_05.02", i, "c0050", "two"); X.exp("DRV-11", "B_05.02", i, "c0050")
    X.new("Total assets negative")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0110", "-" + X.get("B_01.02", i, "c0110")); X.exp("DRV-12", "B_01.02", i, "c0110")
    X.new("Provider total expense negative")
    i = X.pick("B_05.01", (t["B_05.01"]["c0100"] != "") & free()); recon_used.add(i)
    X.set("B_05.01", i, "c0100", "-" + X.get("B_05.01", i, "c0100")); X.exp("DRV-12", "B_05.01", i, "c0100"); X.exp("DRV-46", "B_05.01", i, "c0100")
    X.new("Contract expense negative")
    k, pr = contracts_of_unused_provider(); X.used.setdefault("B_02.01", set()).add(k); recon_used.add(pr); X.used.setdefault("B_05.01", set()).add(pr)
    X.set("B_02.01", k, "c0050", "-" + X.get("B_02.01", k, "c0050")); X.exp("DRV-12", "B_02.01", k, "c0050"); X.exp("DRV-46", "B_05.01", pr, "c0100")

    # ---- date logic ---------------------------------------------------------------------------------------------------
    for _ in range(2):
        X.new("End date earlier than start date")
        i = X.pick("B_02.02", (t["B_02.02"]["c0080"] == "") & (t["B_02.02"]["c0070"] != ""))
        s = date.fromisoformat(X.get("B_02.02", i, "c0070")); X.set("B_02.02", i, "c0080", (s - timedelta(days=30)).isoformat())
        X.exp("DRV-13", "B_02.02", i, "c0080")
    X.new("Function assessed after the reporting date")
    i = X.pick("B_06.01"); X.set("B_06.01", i, "c0070", "2026-03-15"); X.exp("DRV-14", "B_06.01", i, "c0070")
    X.new("Provider audited after the reporting date")
    i = X.pick("B_07.01"); X.set("B_07.01", i, "c0070", "2026-02-01"); X.exp("DRV-14", "B_07.01", i, "c0070")
    X.new("Entity last update dated after the reporting date")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0070", "2026-01-20"); X.exp("DRV-14", "B_01.02", i, "c0070")
    X.new("Entity deleted before it was integrated")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0090", "2024-06-30"); X.exp("DRV-15", "B_01.02", i, "c0090")
    X.new("Entity last update before integration")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0070", "2024-12-01"); X.exp("DRV-15", "B_01.02", i, "c0070")
    X.new("Termination reason without an end date")
    i = X.pick("B_02.02", t["B_02.02"]["c0080"] == ""); X.set("B_02.02", i, "c0090", "Terminated for convenience"); X.exp("DRV-16", "B_02.02", i, "c0090")

    # ---- conditional --------------------------------------------------------------------------------------------------
    X.new("Total assets without currency")
    i = X.pick("B_01.02", t["B_01.02"]["c0060"] != ""); X.set("B_01.02", i, "c0100", ""); X.exp("DRV-17", "B_01.02", i, "c0100")
    X.new("Provider total expense without currency")
    i = X.pick("B_05.01", (t["B_05.01"]["c0100"] != "") & free()); recon_used.add(i); X.set("B_05.01", i, "c0090", ""); X.exp("DRV-17", "B_05.01", i, "c0090")
    X.new("Subsequent arrangement without overarching reference")
    i = X.pick("B_02.01", t["B_02.01"]["c0030"] != ""); X.set("B_02.01", i, "c0030", ""); X.exp("DRV-18", "B_02.01", i, "c0030")
    X.new("Branch flag true but no branch code")
    i = X.pick("B_04.01", t["B_04.01"]["c0030"] == "false"); X.set("B_04.01", i, "c0030", "true"); X.exp("DRV-19", "B_04.01", i, "c0040")
    X.new("Branch code given but flag false")
    i = X.pick("B_04.01", t["B_04.01"]["c0030"] == "true"); X.set("B_04.01", i, "c0030", "false"); X.exp("DRV-19", "B_04.01", i, "c0040")
    X.new("Hard to substitute without a reason")
    i = X.pick("B_07.01", t["B_07.01"]["c0060"] != ""); X.set("B_07.01", i, "c0060", ""); X.exp("DRV-20", "B_07.01", i, "c0060")
    X.new("Critical function without reasons")
    i = X.pick("B_06.01", t["B_06.01"]["c0050"] == "Yes"); X.set("B_06.01", i, "c0060", ""); X.exp("DRV-21", "B_06.01", i, "c0060")
    X.new("Alternatives flagged but not named")
    i = X.pick("B_07.01", t["B_07.01"]["c0110"] == "true"); X.set("B_07.01", i, "c0120", ""); X.exp("DRV-22", "B_07.01", i, "c0120")
    X.new("Data stored but no storage location")
    i = X.pick("B_02.02", t["B_02.02"]["c0140"] == "true"); X.set("B_02.02", i, "c0150", ""); X.exp("DRV-23", "B_02.02", i, "c0150")

    # ---- referential integrity ----------------------------------------------------------------------------------------
    single = t["B_02.02"]["c0010"].map(t["B_02.02"]["c0010"].value_counts()) == 1
    two = ~single
    non_crit = ~t["B_02.02"]["c0050"].isin(crit_fn)
    X.new("Second row of a contract points to a contract that does not exist")
    i = reserved["orchid"]; X.set("B_02.02", i, "c0010", "RC-9999"); X.exp("DRV-30", "B_02.02", i, "c0010")
    X.new("Provider of a second contract row is not in B_05.01 and differs from B_03.02")
    i = reserved["kestrel"]
    X.set("B_02.02", i, "c0030", X.synth[1]); X.exp("DRV-32", "B_02.02", i, "c0030"); X.exp("DRV-41", "B_02.02", i, "c0030")
    X.new("Signing-entity row refers to a contract that does not exist (the real contract loses its row)")
    i = X.pick("B_03.01", t["B_03.01"]["c0010"].str.match(r"RC-\d")); orig = X.get("B_03.01", i, "c0010")
    X.set("B_03.01", i, "c0010", "RC-9998"); X.exp("DRV-30", "B_03.01", i, "c0010")
    X.exp("DRV-40", "B_02.01", int(t["B_02.01"].index[t["B_02.01"]["c0010"] == orig][0]), "c0010")
    X.new("Assessment row carries another existing provider")
    i = X.pick("B_07.01", t["B_07.01"]["c0030"] == "LEI"); cur = X.get("B_07.01", i, "c0020")
    other = [p for p in t["B_05.01"].loc[t["B_05.01"]["c0020"] == "LEI", "c0010"] if p != cur][0]
    X.set("B_07.01", i, "c0020", other); X.exp("DRV-34", "B_07.01", i, "c0020")
    X.new("Assessment row carries a provider that does not exist")
    i = X.pick("B_07.01", t["B_07.01"]["c0030"] == "LEI"); X.set("B_07.01", i, "c0020", X.synth[2])
    X.exp("DRV-32", "B_07.01", i, "c0020"); X.exp("DRV-34", "B_07.01", i, "c0020")
    X.new("Sub-contractor in the supply chain is not in B_05.01")
    i = X.pick("B_05.02", t["B_05.02"]["c0050"] == "1"); X.set("B_05.02", i, "c0060", X.synth[3]); X.exp("DRV-32", "B_05.02", i, "c0060")
    X.new("Ultimate parent of a provider is not in B_05.01")
    selfp = t["B_05.01"]["c0010"] == t["B_05.01"]["c0110"]
    i = X.pick("B_05.01", selfp & (t["B_05.01"]["c0020"] == "LEI") & (t["B_05.01"]["c0100"] != "")); X.set("B_05.01", i, "c0110", X.synth[4])
    X.exp("DRV-32", "B_05.01", i, "c0110")
    X.new("Function identifier does not exist in B_06.01")
    i = X.pick("B_02.02", single & non_crit); X.set("B_02.02", i, "c0050", "F9999"); X.exp("DRV-33", "B_02.02", i, "c0050")
    X.new("Branch code does not exist in B_01.03")
    i = X.pick("B_04.01", t["B_04.01"]["c0030"] == "true"); X.set("B_04.01", i, "c0040", "BR-XX-99"); X.exp("DRV-36", "B_04.01", i, "c0040")
    X.new("Function row carries an entity LEI that is not in B_01.02")
    i = X.pick("B_06.01"); X.set("B_06.01", i, "c0040", X.synth[5]); X.exp("DRV-31", "B_06.01", i, "c0040")
    X.new("Overarching reference does not exist")
    i = X.pick("B_02.01", t["B_02.01"]["c0030"] != ""); X.set("B_02.01", i, "c0030", "RC-M099"); X.exp("DRV-35", "B_02.01", i, "c0030")
    X.new("Overarching reference points to a standalone contract")
    i = X.pick("B_02.01", t["B_02.01"]["c0030"] != "")
    X.set("B_02.01", i, "c0030", t["B_02.01"].loc[t["B_02.01"]["c0020"] == "Standalone arrangement", "c0010"].iloc[0]); X.exp("DRV-35", "B_02.01", i, "c0030")

    # ---- cross-template ----------------------------------------------------------------------------------------------
    X.new("Contract added to B_02.01 with no rows anywhere else")
    j = X.append("B_02.01", ["RC-9001", "Standalone arrangement", "", "EUR", "50000"]); X.exp("DRV-40", "B_02.01", j, "c0010")
    X.new("Provider added to B_05.01 that no contract uses")
    j = X.append("B_05.01", [X.synth[6], "LEI", "", "", "Zephyr Print Services GmbH", "", "Legal person", "DE", "", "", X.synth[6], "LEI"])
    X.exp("DRV-42", "B_05.01", j, "c0010")
    X.new("Non-critical contract re-pointed to a critical function (no assessment, no reliance level)")
    i = X.pick("B_02.02", single & non_crit); crit_id = sorted(crit_fn)[0]; X.set("B_02.02", i, "c0050", crit_id)
    X.exp("DRV-43", "B_02.02", i, "c0010"); X.exp("DRV-44", "B_02.02", i, "c0180")
    X.new("Assessment row added for a non-critical contract")
    src = t["B_07.01"].loc[t["B_07.01"]["c0080"] == "true"].iloc[0].copy()
    j = X.pick("B_02.02", single & non_crit)
    src["c0010"], src["c0020"], src["c0030"], src["c0040"] = (X.get("B_02.02", j, "c0010"), X.get("B_02.02", j, "c0030"),
                                                              X.get("B_02.02", j, "c0040"), X.get("B_02.02", j, "c0060"))
    j = X.append("B_07.01", src); X.exp("DRV-43", "B_07.01", j, "c0010")
    X.new("Level of reliance filled for a non-critical function")
    i = X.pick("B_02.02", non_crit & (t["B_02.02"]["c0180"] == "")); X.set("B_02.02", i, "c0180", "Low reliance"); X.exp("DRV-44", "B_02.02", i, "c0180")
    X.new("Level of reliance blank for a critical function")
    i = X.pick("B_02.02", t["B_02.02"]["c0050"].isin(crit_fn) & (t["B_02.02"]["c0180"] != "")); X.set("B_02.02", i, "c0180", ""); X.exp("DRV-44", "B_02.02", i, "c0180")
    X.new("Critical, not substitutable, but no exit plan")
    i = X.pick("B_07.01", t["B_07.01"]["c0050"].isin(["Not substitutable", "Highly complex substitutability"]) & (t["B_07.01"]["c0080"] == "true"))
    X.set("B_07.01", i, "c0080", "false"); X.exp("DRV-45", "B_07.01", i, "c0080")
    X.new("Provider total 25 percent above the sum of its contracts")
    i = X.pick("B_05.01", (t["B_05.01"]["c0100"] != "") & free())
    recon_used.add(i); X.set("B_05.01", i, "c0100", str(int(int(X.get("B_05.01", i, "c0100")) * 1.25))); X.exp("DRV-46", "B_05.01", i, "c0100")
    X.new("A contract expense 20 percent below what the provider total implies")
    k, pr = contracts_of_unused_provider(); X.used.setdefault("B_02.01", set()).add(k); recon_used.add(pr); X.used.setdefault("B_05.01", set()).add(pr)
    X.set("B_02.01", k, "c0050", str(int(int(X.get("B_02.01", k, "c0050")) * 0.8))); X.exp("DRV-46", "B_05.01", pr, "c0100")
    X.new("Supply chain rank 2 changed to 3 (gap)")
    i = X.pick("B_05.02", (t["B_05.02"]["c0050"] == "2") & (t["B_05.02"]["c0010"] == ref_of[("F0101", 3)]))
    X.set("B_05.02", i, "c0050", "3"); X.exp("DRV-47", "B_05.02", i, "c0050")
    X.new("Sub-contractor is the provider itself")
    i = X.pick("B_05.02", t["B_05.02"]["c0050"] == "1"); X.set("B_05.02", i, "c0060", X.get("B_05.02", i, "c0030")); X.exp("DRV-47", "B_05.02", i, "c0060")

    key = pd.DataFrame(X.key)
    return X.t, key


def build_all() -> Tuple[Tables, Tables, pd.DataFrame]:
    clean = build_clean()
    defective, key = inject(clean)
    write_register(clean, OUT / "clean", "SYNTHETIC register without planted defects. Every name, code and amount is invented.")
    write_register(defective, OUT / "defective", "SYNTHETIC register with planted defects; see answer_key.csv. Every name, code and amount is invented.")
    key.to_csv(OUT / "defective" / "answer_key.csv", index=False)
    return clean, defective, key


if __name__ == "__main__":
    c, d, k = build_all()
    print(f"clean: {sum(len(x) for x in c.values())} rows; defects: {k.defect_id.nunique()}; key rows: {len(k)}")
