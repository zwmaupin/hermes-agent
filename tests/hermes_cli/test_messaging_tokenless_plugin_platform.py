"""#141854 remainder: a token-free *plugin* platform (a2a) must not show "Needs setup" forever.

``builtin_platform_status`` answers only for built-in ids, so the profile-scoped branch fell through
to ``configured = bool(required) and all(...)`` — always False when ``required_env`` is empty. A
plugin platform with no required env var therefore read as not configured no matter how the operator
switched it on, and the dashboard kept offering setup.
"""
from __future__ import annotations

from unittest.mock import patch

from hermes_cli.web_routers import messaging


def _entry(required_env: list[str]) -> dict:
    return {"required_env": required_env, "env_vars": required_env}


def _enablement(platform_id, entry, env_on_disk, config, *, status=None):
    with patch.object(messaging, "load_config", return_value=config), \
            patch.object(messaging, "builtin_platform_status", return_value=status):
        return messaging._platform_enablement(platform_id, entry, env_on_disk, scoped=True)


def test_plugin_platform_with_no_required_env_is_configured_once_enabled_in_config():
    enabled, configured, home = _enablement(
        "a2a", _entry([]), {}, {"platforms": {"a2a": {"enabled": True}}})
    assert (enabled, configured, home) == (True, True, None)


def test_plugin_platform_with_no_required_env_is_configured_by_its_enabled_flag():
    enabled, configured, _ = _enablement(
        "a2a", _entry([]), {"A2A_ENABLED": "true"}, {})
    assert (enabled, configured) == (True, True)


def test_plugin_platform_explicit_disable_still_wins_over_the_env_flag():
    enabled, configured, _ = _enablement(
        "a2a", _entry([]), {"A2A_ENABLED": "true"}, {"platforms": {"a2a": {"enabled": False}}})
    assert (enabled, configured) == (False, False)


def test_plugin_platform_untouched_reports_not_configured():
    enabled, configured, _ = _enablement("a2a", _entry([]), {}, {})
    assert (enabled, configured) == (False, False)


def test_platform_with_required_env_still_needs_the_credential():
    enabled, configured, _ = _enablement(
        "a2a", _entry(["A2A_TOKEN"]), {}, {"platforms": {"a2a": {"enabled": True}}})
    assert (enabled, configured) == (True, False), "a required credential must still gate setup"


def test_builtin_verdict_is_not_overwritten_for_builtin_platforms():
    # webhook has no required env var and does go through builtin_platform_status; the new arm must
    # only run when that function has no verdict for the id.
    enabled, configured, _ = _enablement(
        "webhook", _entry([]), {}, {"platforms": {"webhook": {"enabled": True}}}, status=(True, True))
    assert (enabled, configured) == (True, True)
