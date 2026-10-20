"""#141854: token-free platforms must report configured when enabled via config.yaml
or the <ID>_ENABLED env flag, not show "Needs setup" forever.
"""
from __future__ import annotations

from unittest.mock import patch

from hermes_cli.web_routers.messaging import _env_flag_on, _platform_enablement


def _entry(required_env: list[str]) -> dict:
    return {"required_env": required_env, "env_vars": required_env}


def test_env_flag_on():
    """_env_flag_on recognizes truthy env var values."""
    assert _env_flag_on("1") is True
    assert _env_flag_on("true") is True
    assert _env_flag_on("True") is True
    assert _env_flag_on("yes") is True
    assert _env_flag_on("on") is True
    assert _env_flag_on("0") is False
    assert _env_flag_on("false") is False
    assert _env_flag_on("") is False
    assert _env_flag_on(None) is False


def test_token_free_platform_enabled_via_config_yaml():
    """A token-free platform with enabled: true in config.yaml reports configured."""
    entry = _entry([])
    env_on_disk: dict[str, str] = {}
    with patch("hermes_cli.web_routers.messaging.load_config") as mock_lc:
        mock_lc.return_value = {"platforms": {"whatsapp": {"enabled": True}}}
        enabled, configured, _ = _platform_enablement("whatsapp", entry, env_on_disk, scoped=True)
    assert enabled is True
    assert configured is True


def test_token_free_platform_enabled_via_env_flag():
    """A token-free platform with <ID>_ENABLED=true in .env reports configured."""
    entry = _entry([])
    env_on_disk = {"WHATSAPP_ENABLED": "true"}
    with patch("hermes_cli.web_routers.messaging.load_config") as mock_lc:
        mock_lc.return_value = {}
        enabled, configured, _ = _platform_enablement("whatsapp", entry, env_on_disk, scoped=True)
    assert enabled is True
    assert configured is True


def test_token_free_platform_explicit_disable_wins():
    """A token-free platform with enabled: false in config.yaml reports not configured."""
    entry = _entry([])
    env_on_disk = {"WHATSAPP_ENABLED": "true"}
    with patch("hermes_cli.web_routers.messaging.load_config") as mock_lc:
        mock_lc.return_value = {"platforms": {"whatsapp": {"enabled": False}}}
        enabled, configured, _ = _platform_enablement("whatsapp", entry, env_on_disk, scoped=True)
    assert enabled is False
    assert configured is False


def test_token_free_platform_nothing_set():
    """A token-free platform with nothing set reports not configured."""
    entry = _entry([])
    env_on_disk: dict[str, str] = {}
    with patch("hermes_cli.web_routers.messaging.load_config") as mock_lc:
        mock_lc.return_value = {}
        enabled, configured, _ = _platform_enablement("whatsapp", entry, env_on_disk, scoped=True)
    assert enabled is False
    assert configured is False


def test_credentialed_platform_still_requires_token():
    """A credentialed platform still requires its token to report configured."""
    entry = _entry(["TELEGRAM_BOT_TOKEN"])
    env_on_disk: dict[str, str] = {}
    with patch("hermes_cli.web_routers.messaging.load_config") as mock_lc:
        mock_lc.return_value = {"platforms": {"telegram": {"enabled": True}}}
        enabled, configured, _ = _platform_enablement("telegram", entry, env_on_disk, scoped=True)
    assert enabled is True
    assert configured is False  # token missing

    env_on_disk = {"TELEGRAM_BOT_TOKEN": "abc123"}
    with patch("hermes_cli.web_routers.messaging.load_config") as mock_lc:
        mock_lc.return_value = {"platforms": {"telegram": {"enabled": True}}}
        enabled, configured, _ = _platform_enablement("telegram", entry, env_on_disk, scoped=True)
    assert enabled is True
    assert configured is True  # token present


def test_token_free_platform_env_flag_variants():
    """Various truthy/falsy env flag values for token-free platforms."""
    entry = _entry([])
    for value, expected in [("1", True), ("true", True), ("TRUE", True), ("yes", True), ("on", True),
                            ("0", False), ("false", False), ("", False), (None, False)]:
        env_on_disk = {"WHATSAPP_ENABLED": value} if value is not None else {}
        with patch("hermes_cli.web_routers.messaging.load_config") as mock_lc:
            mock_lc.return_value = {}
            _, configured, _ = _platform_enablement("whatsapp", entry, env_on_disk, scoped=True)
        assert configured is expected, f"WHATSAPP_ENABLED={value!r} should give configured={expected}"
