"""A copied profile can't decrypt app-bound cookies, so the copy silently loses its session.

Chromium/Edge store cookies encrypted with app-bound encryption (``encrypted_value`` prefix
``v20``). Those rows only decrypt inside the browser context that wrote them, so a copied profile
hands them to the copy browser, which deletes every row it can't decrypt on first load. The
snapshot itself is lossless, so nothing in the launch path noticed and the agent was free to
report a signed-in browser that is signed out (#96993).

Contract: after the cookie overlay, the snapshot records how many app-bound rows the copy holds
and exposes a warning saying what will happen. Detection never fails the snapshot — real-profile
browsing keeps working, the user just gets told the truth.
"""
import json
import os
import sqlite3

import hermes_cli.browser_connect as bc

_APP_BOUND = b"v20" + b"\x11" * 96
_DPAPI = b"v10" + b"\x22" * 96


def _cookie_db(path, rows):
    """A Cookies DB shaped like Chromium's: one (name, value, encrypted_value) per row."""
    con = sqlite3.connect(path)
    con.execute("create table cookies(name text, value text, encrypted_value blob)")
    con.executemany("insert into cookies values (?,?,?)", rows)
    con.commit()
    con.close()


def _fake_profile(root, rows):
    (root / "Default" / "Network").mkdir(parents=True)
    (root / "Local State").write_text(json.dumps({"profile": {"last_used": "Default"}}), encoding="utf-8")
    (root / "Default" / "Preferences").write_text("{}", encoding="utf-8")
    _cookie_db(str(root / "Default" / "Network" / "Cookies"), rows)


def test_snapshot_records_app_bound_cookies_and_warns_about_signed_out(tmp_path, monkeypatch):
    root = tmp_path / "real"
    rows = [(f"v{i}", "", _APP_BOUND) for i in range(6)] + [("plain", "x", b"")]
    _fake_profile(root, rows)
    monkeypatch.setattr(bc, "get_hermes_home", lambda: tmp_path / "hh")

    dst, err = bc.snapshot_real_profile("chrome", src=str(root))

    assert err is None and dst
    # The copy is lossless: the rows are present, they are just undecryptable here.
    assert bc.count_app_bound_cookies(dst) == 6
    warning = bc.app_bound_cookie_warning(dst)
    assert warning and "signed out" in warning.lower()
    assert "6" in warning


def test_no_warning_when_every_cookie_row_is_decryptable(tmp_path, monkeypatch):
    root = tmp_path / "real"
    _fake_profile(root, [("dpapi", "", _DPAPI), ("plain", "x", b"")])
    monkeypatch.setattr(bc, "get_hermes_home", lambda: tmp_path / "hh")

    dst, err = bc.snapshot_real_profile("chrome", src=str(root))

    assert err is None and dst
    assert bc.count_app_bound_cookies(dst) == 0
    assert bc.app_bound_cookie_warning(dst) is None


def test_count_and_warning_tolerate_a_profile_without_a_cookie_db(tmp_path):
    empty = tmp_path / "nothing"
    empty.mkdir()
    assert bc.count_app_bound_cookies(str(empty)) == 0
    assert bc.app_bound_cookie_warning(str(empty)) is None


def test_warning_survives_a_locked_profile_reuse(tmp_path, monkeypatch):
    """A locked live profile reuses the last snapshot; the recorded warning must still describe it,
    because that is exactly the copy being served."""
    root = tmp_path / "real"
    _fake_profile(root, [("v0", "", _APP_BOUND)])
    monkeypatch.setattr(bc, "get_hermes_home", lambda: tmp_path / "hh")
    dst, err = bc.snapshot_real_profile("chrome", src=str(root))
    assert err is None and dst

    monkeypatch.setattr(bc, "_profile_is_locked", lambda *a, **k: True)
    dst2, err2 = bc.snapshot_real_profile("chrome", src=str(root))

    assert err2 is None and dst2 == dst
    assert bc.app_bound_cookie_warning(dst2)
