"""Reference lists: ISO codes, closed lists (simplified labels), thresholds."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "data" / "reference"

# ISO 3166-1 alpha-2 (249 officially assigned codes). EBA rule VR_16 asks for a valid country code.
COUNTRIES = frozenset("""
AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ
CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR
GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO
JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR
MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO
RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV
TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW
""".split())

# ISO 4217 active alphabetic codes (snapshot; refresh from the ISO 4217 maintenance agency before real use).
CURRENCIES = frozenset("""
AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD CAD CDF CHF CLP
CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR
ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT
MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD
SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND
VUV WST XAF XCD XOF XPF YER ZAR ZMW ZWG
""".split())

EU_MEMBERS = frozenset("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())

# Closed lists. The official submission uses DPM member codes (for example eba_CO:x3); these are readable,
# simplified labels. The ones marked [EBA] are tied to a published rule, the others follow the ITS templates loosely.
VOCAB = {
    "entity_type": ["Credit institution", "Investment firm", "Payment institution", "Insurance undertaking",
                    "Crypto-asset service provider"],
    "hierarchy": ["Parent undertaking", "Subsidiary"],
    # [EBA] rules v8805_m / v22912_m: member x3 needs an overarching reference; x3 is read here as "Subsequent or associated"
    "arrangement_type": ["Standalone arrangement", "Overarching/master agreement", "Subsequent or associated arrangement"],
    "code_type": ["LEI", "EUID"],
    "service_type": [
        "Cloud services: IaaS", "Cloud services: PaaS", "Cloud services: SaaS",
        "ICT, facilities and hosting services (excluding Cloud services)", "Software licencing (excluding SaaS)",
        "ICT operation management (including maintenance)", "ICT security management services", "Provision of data",
        "Data analysis", "Non-Cloud Data storage", "Telecommunication carrier", "Network Infrastructure",
        "Hardware and physical devices", "ICT help desk and first level support", "ICT Consulting",
    ],
    "termination_reason": ["Expired", "Terminated for convenience", "Terminated for breach", "Terminated by provider"],
    "person_type": ["Legal person", "Individual acting in a business capacity"],
    "yes_no": ["Yes", "No"],
    # [EBA] rule v8825_m: two members of this list require a reason (read here as the two hardest levels)
    "substitutability": ["Not substitutable", "Highly complex substitutability", "Medium complexity", "Low complexity",
                         "Easily substitutable"],
    "reintegration": ["Easy", "Difficult", "Highly complex"],
    "impact": ["Low", "Medium", "High"],
    "sensitivity": ["Low", "Moderate", "High"],
    "reliance": ["Low reliance", "Medium reliance", "High reliance", "Full reliance"],
}
HARD_TO_SUBSTITUTE = ("Not substitutable", "Highly complex substitutability")
BOOL_VALUES = ("true", "false", "1", "0")  # EBA technical check 332
TRUE_VALUES = ("true", "1")

# Concentration thresholds (illustrative, for a review conversation, not a regulatory limit).
THRESHOLDS = {
    "provider_spend_share": 0.20,       # CON-01: share of total annual ICT spend, per ultimate parent group
    "critical_functions_supported": 4,  # CON-02: distinct critical or important functions per ultimate parent group
    "third_country_spend_share": 0.30,  # CON-03: share of spend with one non-EU ultimate-parent country
}
SPEND_TOLERANCE = 1.0  # DRV-46: absolute tolerance in currency units


def load_fx() -> dict:
    with open(REF / "fx_illustrative.csv", newline="") as f:
        return {r["currency"]: float(r["eur_per_unit"]) for r in csv.DictReader(f)}


def load_real_leis() -> list:
    with open(REF / "real_lei_samples.csv", newline="") as f:
        return list(csv.DictReader(f))
