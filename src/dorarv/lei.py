"""LEI (ISO 17442) format and check digits (ISO 7064 MOD 97-10)."""
from __future__ import annotations

import random
import re
import string

LEI_FORMAT = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")  # the pattern used by EBA rules v8826_m / v8890_m / v8891_m / v8892_m
_ALNUM = string.ascii_uppercase + string.digits


def _digits(s: str) -> str:
    """Letters become 10..35, digits stay: the numeric string the mod-97 check runs on."""
    return "".join(str(int(c, 36)) for c in s)


def has_valid_format(lei: str) -> bool:
    return bool(LEI_FORMAT.match(lei or ""))


def has_valid_checksum(lei: str) -> bool:
    """True when the 20 characters, read as a number, leave remainder 1 modulo 97."""
    if not has_valid_format(lei):
        return False
    return int(_digits(lei)) % 97 == 1


def check_digits(base18: str) -> str:
    """The two check digits that complete an 18-character base."""
    return f"{98 - int(_digits(base18) + '00') % 97:02d}"


def make_lei(rng: random.Random, prefix: str = "") -> str:
    """A well-formed LEI with valid check digits. Not registered anywhere: the prefix and the random
    body make a code that no GLEIF record is expected to carry."""
    body = prefix + "".join(rng.choice(_ALNUM) for _ in range(18 - len(prefix)))
    return body + check_digits(body)
