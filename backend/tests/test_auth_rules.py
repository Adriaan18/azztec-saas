"""
Azztec_SaaS_backend_tests_test_auth_rules_v1_0_0.py  ->  backend/tests/test_auth_rules.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s3, s7, OD-96..OD-100
Pair of:  app/auth/rules.py 1.0.0

Pure, zero DB. The MD5-20 vectors are the ones SQL Server's own HASHBYTES produced for the 2026-11-06
default-password count (7 accounts), so a Python/T-SQL disagreement would show here first.

Changelog:
  1.0.0  Initial DP2a. 22 tests, 33 cases once parametrised.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.auth import rules

NOW = datetime(2026, 11, 7, 9, 0, 0)


# ---------------------------------------------------------------------------
# password (OD-96, traps 1-3)
# ---------------------------------------------------------------------------


def test_md5_20_matches_workmate_net_vectors():
    assert rules.md5_20("wm") == "958142E7545CB1226DD8"
    assert rules.md5_20("sys_user") == "EF57532DA60B6024567F"
    assert len(rules.md5_20("anything at all")) == 20


def test_non_ascii_becomes_a_question_mark_like_encoding_ascii():
    assert rules.md5_20("café") == rules.md5_20("caf?")


def test_password_matches_trims_the_stored_value_only():
    stored = rules.md5_20("Secret1") + "   "  # char(20) is exact, but a padded read must not matter
    assert rules.password_matches(stored, "Secret1")
    assert rules.password_matches(stored.lower(), "Secret1")
    assert not rules.password_matches(stored, " Secret1")  # the typed text is hashed as typed
    assert not rules.password_matches(stored, "Secret1 ")


def test_password_matches_refuses_blank_and_wrong():
    assert not rules.password_matches(None, "x")
    assert not rules.password_matches("", "x")
    assert not rules.password_matches(rules.md5_20("a"), "b")
    assert not rules.password_matches(rules.DUMMY_STORED, "")


# ---------------------------------------------------------------------------
# login (trap 9)
# ---------------------------------------------------------------------------


def test_login_keeps_inner_spaces_and_clips():
    assert rules.normalise_login("  Kevin E  ") == "kevin e"
    assert rules.clip_login("  Kevin E  ") == "Kevin E"
    assert len(rules.clip_login("x" * 300)) == rules.LOGIN_MAX


# ---------------------------------------------------------------------------
# refusal (OD-98)
# ---------------------------------------------------------------------------


def test_sys_user_is_refused_first_whatever_else_is_true():
    assert rules.refusal(" sys_user ", "wm", "sys_user", False, True) == "SYS_USER"


@pytest.mark.parametrize("pw", ["wm", "WM", "sys_user", "Sys_User", "jsmith", "JSMITH"])
def test_default_passwords_and_the_login_id_are_refused(pw):
    assert rules.refusal("JS", pw, "jsmith", True, False) == "DEFAULT_PASSWORD"


def test_no_group_then_reset_due_in_that_order():
    assert rules.refusal("JS", "Good-Pass1", "jsmith", False, True) == "NO_GROUP"
    assert rules.refusal("JS", "Good-Pass1", "jsmith", True, True) == "RESET_DUE"
    assert rules.refusal("JS", "Good-Pass1", "jsmith", True, False) is None


def test_every_reason_has_a_message():
    for code in ("SIGNIN_FAILED", "LOCKED", "SYS_USER", "DEFAULT_PASSWORD", "NO_GROUP", "RESET_DUE"):
        assert rules.MESSAGES[code].endswith(".")


def test_reset_policy_off_at_rst_refuses_nobody():
    # P2: PW_RESET_PERIOD = 0, PW_Sec_Level = 1
    assert not rules.reset_due(1, 0, "", None, NOW.date())
    assert not rules.reset_due(1, 0, "1", date(2001, 1, 1), NOW.date())


def test_reset_policy_when_a_client_turns_it_on():
    today = NOW.date()
    assert rules.reset_due(2, 0, "1", None, today)
    assert rules.reset_due(2, 0, "", None, today)
    assert not rules.reset_due(2, 0, "0", None, today)
    assert rules.reset_due(1, 3, "0", None, today)  # no date counts as due
    assert rules.reset_due(1, 3, "0", date(2026, 8, 7), today)  # exactly 3 months
    assert not rules.reset_due(1, 3, "0", date(2026, 8, 8), today)


def test_add_months_clamps_the_day():
    assert rules.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert rules.add_months(date(2026, 11, 7), 3) == date(2027, 2, 7)


# ---------------------------------------------------------------------------
# rights (OD-100, s3.2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "level,right", [(1, "RWD"), (2, "RWD"), (3, "RW"), (4, "RO"), (0, "NA"), (None, "NA"), (5, "NA")]
)
def test_level_right(level, right):
    assert rules.level_right(level) == right


def test_tag_right_defaults_to_rwd():
    assert rules.tag_right(None) == "RWD"
    assert rules.tag_right("") == "RWD"
    assert rules.tag_right("garbage") == "RWD"
    assert rules.tag_right(" ro ") == "RO"


def test_effective_is_the_more_restrictive():
    assert rules.effective("RWD", "RO") == "RO"
    assert rules.effective("RO", "RWD") == "RO"
    assert rules.effective("RW", "NA") == "NA"


def test_page_rights_rst_shapes():
    """P4/P5: Schedulex has rows for PLANNER (RWD) and READ ONLY (RO) only; WOMaint for eight groups."""
    planner_tag = rules.PAGE_TAGS["planner"]
    womaint_tag = rules.PAGE_TAGS["womaint"]
    assert rules.page_rights(3, {}) == {"planner": "RW", "womaint": "RW"}  # Operator: no rows
    assert rules.page_rights(4, {planner_tag: "RO", womaint_tag: "RO"}) == {"planner": "RO", "womaint": "RO"}
    assert rules.page_rights(1, {}) == {"planner": "RWD", "womaint": "RWD"}  # Andrew
    assert rules.page_rights(None, {}) == {"planner": "NA", "womaint": "NA"}  # no group
    assert rules.page_rights(1, {planner_tag: "NA"})["planner"] == "NA"


def test_admin_is_level_exactly_one():
    assert rules.is_admin(1) and not rules.is_admin(2) and not rules.is_admin(None)


def test_allows():
    assert rules.allows("RW", "RO") and rules.allows("RW", "RW") and not rules.allows("RO", "RW")
    assert not rules.allows("NA", "RO") and not rules.allows("bogus", "RO")


# ---------------------------------------------------------------------------
# lockout (OD-99) and sessions (OD-97)
# ---------------------------------------------------------------------------


def test_lockout_thresholds():
    assert rules.lockout(4, 19) is None
    assert rules.lockout(5, 0) == "LOGIN"
    assert rules.lockout(0, 20) == "IP"


def test_token_hash_is_64_lowercase_hex_and_never_the_token():
    h = rules.token_hash("abc")
    assert len(h) == 64 and h == h.lower() and "abc" not in h


def test_session_state():
    exp = NOW + timedelta(hours=12)
    assert rules.session_state(NOW, NOW, exp, None, 240) == "ok"
    assert rules.session_state(NOW, NOW, exp, NOW, 240) == "revoked"
    assert rules.session_state(exp, exp - timedelta(minutes=1), exp, None, 240) == "expired"
    assert rules.session_state(NOW, NOW - timedelta(minutes=240), exp, None, 240) == "idle"
    assert rules.session_state(NOW, NOW - timedelta(minutes=239), exp, None, 240) == "ok"


def test_needs_touch_once_a_minute():
    assert rules.needs_touch(NOW, None)
    assert not rules.needs_touch(NOW, NOW - timedelta(seconds=59))
    assert rules.needs_touch(NOW, NOW - timedelta(seconds=60))
