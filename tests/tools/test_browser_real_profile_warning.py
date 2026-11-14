"""The app-bound copy warning has to reach the model, not just the log.

``app_bound_cookie_warning()`` records what the snapshot holds (#96993). A warning nobody reads is
the same bug with more code: these cover the two seams that carry it out of ``hermes_cli`` — the
per-home lookup the session layer attaches to a real-profile session, and the browser_exec result
that tells the agent the browser it drives may read signed out.
"""
import json

from tools import browser_session_real_profile as rp
from tools import browser_use_cli as bu


def _snapshot(root, browser, rows):
    d = root / "browser-profile" / browser
    d.mkdir(parents=True)
    (d / ".hermes-snapshot-complete").write_text("Default", encoding="utf-8")
    (d / ".hermes-snapshot-app-bound-cookies").write_text(str(rows), encoding="utf-8")
    return d


def test_home_warning_reports_the_snapshot_holding_app_bound_cookies(tmp_path):
    _snapshot(tmp_path, "edge", 6)
    warning = rp.real_profile_cookie_warning(str(tmp_path))
    assert warning and "signed out" in warning.lower()
    assert "6" in warning


def test_home_warning_is_silent_without_a_snapshot_or_with_zero_rows(tmp_path):
    assert rp.real_profile_cookie_warning(str(tmp_path)) is None
    _snapshot(tmp_path, "edge", 0)
    assert rp.real_profile_cookie_warning(str(tmp_path)) is None


def test_result_carries_the_warning_once_per_route():
    bu._real_profile_cookie_warning["route-a"] = "9 cookies are app-bound encrypted"
    bu._real_profile_cookie_note_delivered.discard("route-a")

    first = bu._take_real_profile_note("route-a")
    assert first == {"real_profile_cookie_warning": "9 cookies are app-bound encrypted"}

    assert bu._take_real_profile_note("route-a") == {}
    bu._real_profile_cookie_warning.pop("route-a", None)
    bu._real_profile_cookie_note_delivered.discard("route-a")
