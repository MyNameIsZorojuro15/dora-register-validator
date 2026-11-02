import random

import pytest

from dorarv import lei
from dorarv.reference import load_real_leis


def test_real_public_leis_pass_the_check_digits():
    real = load_real_leis()
    assert len(real) >= 5
    for r in real:
        assert lei.has_valid_format(r["lei"]) and lei.has_valid_checksum(r["lei"]), r["entity"]


def test_check_digits_are_computed_the_iso_7064_way():
    # the LEI quoted on the GLEIF page: base 506700GE1G29325QX3 + check digits 63
    assert lei.check_digits("506700GE1G29325QX3") == "63"
    # worked by hand: "A" -> 10, "Z" -> 35; the whole 20-character code read as a number leaves remainder 1 modulo 97
    assert int(lei._digits("506700GE1G29325QX363")) % 97 == 1


def test_generated_leis_are_valid_and_distinct():
    rng = random.Random(7)
    codes = {lei.make_lei(rng, "SYNT") for _ in range(500)}
    assert len(codes) == 500
    assert all(lei.has_valid_format(c) and lei.has_valid_checksum(c) and c.startswith("SYNT") for c in codes)


def test_single_character_errors_are_caught_digit_swaps_always_and_the_rest_almost_always():
    """MOD 97-10 turns a letter into two digits, so a few digit-for-letter slips can pass. Measured, not assumed."""
    rng = random.Random(11)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    total = missed = 0
    for _ in range(40):
        good = lei.make_lei(rng)
        for pos in range(20):
            for ch in alphabet:
                if ch == good[pos] or (pos >= 18 and not ch.isdigit()):
                    continue
                bad = good[:pos] + ch + good[pos + 1:]
                ok = lei.has_valid_checksum(bad)
                if ch.isdigit() and good[pos].isdigit():
                    assert not ok, (good, bad)
                total += 1
                missed += ok
    assert missed / total < 0.01


def test_most_adjacent_transpositions_are_caught():
    rng = random.Random(13)
    total = caught = 0
    for _ in range(50):
        good = lei.make_lei(rng)
        for pos in range(17):
            if good[pos] != good[pos + 1]:
                bad = good[:pos] + good[pos + 1] + good[pos] + good[pos + 2:]
                total += 1
                caught += not lei.has_valid_checksum(bad)
    assert caught / total > 0.95


@pytest.mark.parametrize("code", ["", "506700GE1G29325QX36", "506700GE1G29325QX3630", "506700ge1g29325qx363",
                                  "506700GE1G29325QX3AB", "506700GE1G29325QX36!", " 506700GE1G29325QX363"])
def test_bad_format_is_rejected(code):
    assert not lei.has_valid_format(code)
    assert not lei.has_valid_checksum(code)


def test_wrong_check_digits_are_rejected_though_the_format_is_fine():
    assert lei.has_valid_format("506700GE1G29325QX364")
    assert not lei.has_valid_checksum("506700GE1G29325QX364")
