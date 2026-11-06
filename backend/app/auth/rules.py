"""
Azztec_SaaS_app_auth_rules_v1_0_0.py  ->  backend/app/auth/rules.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s3.1, s3.2, OD-96..OD-100 (signed 2026-11-06)
Pair of:  backend/tests/test_auth_rules.py 1.0.0

Pure. No database, no request, no clock (callers pass `now`). Everything a sign-in or a gate decides is
decided here, so the order of the rules is one place to read and one place to test.

  password    Workmate.NET's check: uppercase hex MD5 of the ASCII bytes of the text AS TYPED, first 20
              characters, against Users.AD_Password trimmed (frmLogin.cs 175, clsGeneralOperation.cs
              1377). Encoding.ASCII turns every non-ASCII character into '?'; encode('ascii', 'replace')
              does the same. Compared in constant time. Verify only - nothing here ever produces a hash
              to be stored (OD-96).
  refusal     OD-98 rules 3..6, reached only after the password is proved: SYS_USER, a default password
              (wm, sys_user, or the person's own login id in any case), no security group, Workmate.NET's
              own reset policy.
  rights      the Ignition workmate.security 1.9.0 model (s3.2): level from the lowest group, page right
              from that group's menu tag (no row -> RWD), effective = the more restrictive (D6-A).
              Administrator = level exactly 1.
  lockout     OD-99: 5 failures for a login, or 20 for an address, in the window.
  sessions    OD-97: 12 h absolute, 4 h idle, last-seen refreshed at most once a minute.

Changelog:
  1.0.0  Initial DP2a.
"""

from __future__ import annotations

import calendar
import hashlib
import hmac
from datetime import date, datetime, timedelta

__version__ = "1.0.0"

# Perspective / SaaS page key -> legacy System_Menu.Menu_Tag (the .NET ToolStripMenuItem name)
PAGE_TAGS: dict[str, str] = {
    "planner": "workmateSchedulexToolStripMenuItem",  # Option A, chosen 2026-11-06
    "womaint": "workmateOrderMaintananceToolStripMenuItem",
}

RANK: dict[str, int] = {"NA": 0, "RO": 1, "RW": 2, "RWD": 3}
BY_RANK: tuple[str, ...] = ("NA", "RO", "RW", "RWD")
ADMIN_LEVEL = 1
SYS_USER = "SYS_USER"
KNOWN_DEFAULTS: tuple[str, ...] = ("wm", "sys_user")
LOGIN_MAX = 100

MESSAGES: dict[str, str] = {
    "SIGNIN_FAILED": "Sign-in failed. Check your user name and password.",
    "LOCKED": "Too many failed sign-ins. Wait 15 minutes, then try again.",
    "SYS_USER": "This account can't sign in to Azztec.",
    "DEFAULT_PASSWORD": (
        "Your password is a default one, or the same as your user name. "
        "Change it in Workmate.NET first, then sign in here."
    ),
    "NO_GROUP": (
        "Your Workmate account isn't in a security group yet. Ask your Workmate administrator to add you."
    ),
    "RESET_DUE": "Workmate.NET wants a new password from you. Change it there first, then sign in here.",
}


# ---------------------------------------------------------------------------
# password (OD-96)
# ---------------------------------------------------------------------------


def md5_20(text: str) -> str:
    """Workmate.NET's CreateMD5Hash(text).Substring(0, 20): uppercase hex MD5 of the ASCII bytes."""
    return hashlib.md5(text.encode("ascii", "replace")).hexdigest().upper()[:20]  # legacy, verify only


DUMMY_STORED = md5_20("azztec-no-such-user")  # compared against when the login is unknown (trap 6)


def password_matches(stored: str | None, typed: str) -> bool:
    """Stored char(20) value (trimmed, any case) against the typed text (NOT trimmed - trap 1)."""
    want = (stored or "").strip().upper()
    if not want:
        return False
    return hmac.compare_digest(want, md5_20(typed))


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


def clip_login(typed: str) -> str:
    """The login as typed, for the audit row: ends trimmed, at most LOGIN_MAX characters."""
    return (typed or "").strip()[:LOGIN_MAX]


def normalise_login(typed: str) -> str:
    """The comparison key: ends trimmed and lower-cased. An inner space is kept (trap 9: 112 at RST)."""
    return clip_login(typed).lower()


# ---------------------------------------------------------------------------
# refusal (OD-98 rules 3..6 - only ever asked after the password is proved)
# ---------------------------------------------------------------------------


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def reset_due(
    sec_level: int, period_months: int, reset_flag: str | None, last_reset: date | None, today: date
) -> bool:
    """Workmate.NET's own reset policy (frmLogin.cs 184): PW_Sec_Level > 1 with Reset_Pwd_flag 1 or
    empty, or PW_RESET_PERIOD months since Last_PW_Reset_Date (a missing date counts as due)."""
    if sec_level > 1 and (reset_flag or "").strip() in ("1", ""):
        return True
    if period_months > 0:
        return last_reset is None or add_months(last_reset, period_months) <= today
    return False


def refusal(
    short_id: str, typed_password: str, login_id: str, has_group: bool, reset_is_due: bool
) -> str | None:
    """None when the person may sign in, else the reason code. The order is the spec's."""
    if (short_id or "").strip().upper() == SYS_USER:
        return "SYS_USER"
    pw = typed_password.lower()
    if pw in KNOWN_DEFAULTS or pw == (login_id or "").strip().lower():
        return "DEFAULT_PASSWORD"
    if not has_group:
        return "NO_GROUP"
    if reset_is_due:
        return "RESET_DUE"
    return None


# ---------------------------------------------------------------------------
# rights (OD-100)
# ---------------------------------------------------------------------------


def level_right(level: int | None) -> str:
    """Security_Group.Sec_Group_Access_Level -> right. 1-2 RWD, 3 RW, 4 RO, anything else NA (D5)."""
    if level in (1, 2):
        return "RWD"
    if level == 3:
        return "RW"
    if level == 4:
        return "RO"
    return "NA"


def tag_right(value: str | None) -> str:
    """A System_Menu_Security_Group.Menu_Access_Level. Missing or unreadable -> RWD (the .NET seed)."""
    v = (value or "").strip().upper()
    return v if v in RANK else "RWD"


def effective(level_r: str, tag_r: str) -> str:
    """The more restrictive of the two (D6-A)."""
    return BY_RANK[min(RANK[level_r], RANK[tag_r])]


def page_rights(level: int | None, tag_rows: dict[str, str]) -> dict[str, str]:
    """{page: right} for every PAGE_TAGS page. tag_rows maps Menu_Tag -> Menu_Access_Level for the
    user's group; a tag with no row is RWD on the tag side, so the level decides."""
    lr = level_right(level)
    return {page: effective(lr, tag_right(tag_rows.get(tag))) for page, tag in PAGE_TAGS.items()}


def is_admin(level: int | None) -> bool:
    return level == ADMIN_LEVEL


def allows(have: str, need: str) -> bool:
    return RANK.get(have, 0) >= RANK[need]


# ---------------------------------------------------------------------------
# lockout (OD-99)
# ---------------------------------------------------------------------------


def lockout(login_failures: int, ip_failures: int, max_login: int = 5, max_ip: int = 20) -> str | None:
    """'LOGIN' or 'IP' when the attempt must be refused before the password is even looked at."""
    if login_failures >= max_login:
        return "LOGIN"
    if ip_failures >= max_ip:
        return "IP"
    return None


# ---------------------------------------------------------------------------
# sessions (OD-97)
# ---------------------------------------------------------------------------


def token_hash(token: str) -> str:
    """What the database keeps instead of the cookie value: lowercase hex SHA-256, 64 characters."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def expires_at(now: datetime, hours: int) -> datetime:
    return now + timedelta(hours=hours)


def session_state(
    now: datetime,
    last_seen: datetime | None,
    expires: datetime | None,
    revoked: datetime | None,
    idle_minutes: int,
) -> str:
    """'ok' | 'revoked' | 'expired' | 'idle'."""
    if revoked is not None:
        return "revoked"
    if expires is None or now >= expires:
        return "expired"
    if last_seen is None or now - last_seen >= timedelta(minutes=idle_minutes):
        return "idle"
    return "ok"


def needs_touch(now: datetime, last_seen: datetime | None, every_seconds: int = 60) -> bool:
    return last_seen is None or (now - last_seen).total_seconds() >= every_seconds
