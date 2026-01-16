"""Tests for secret resolution."""

from typing import Any

import pytest

from poni.config.secrets import load_env_secrets, resolve_secrets


class TestLoadEnvSecrets:
    """Tests for load_env_secrets function."""

    def test_loads_from_env(self, monkeypatch: Any) -> None:
        """Test loading secrets from environment."""
        monkeypatch.setenv("TEST_SECRET", "from_env")
        secrets = load_env_secrets()
        assert secrets["TEST_SECRET"] == "from_env"

    def test_loads_from_env_file(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Test loading secrets from .env file."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("FILE_SECRET=from_file\n")

        secrets = load_env_secrets()
        assert secrets["FILE_SECRET"] == "from_file"

    def test_env_overrides_file(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Test environment variables override .env file."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("OVERRIDE_SECRET=from_file\n")
        monkeypatch.setenv("OVERRIDE_SECRET", "from_env")

        secrets = load_env_secrets()
        assert secrets["OVERRIDE_SECRET"] == "from_env"


class TestResolveSecrets:
    """Tests for resolve_secrets function."""

    def test_resolve_string(self) -> None:
        """Test resolving a simple string."""
        secrets = {"API_KEY": "secret123"}
        result = resolve_secrets("key=${API_KEY}", secrets)
        assert result == "key=secret123"

    def test_resolve_multiple(self) -> None:
        """Test resolving multiple secrets in one string."""
        secrets = {"USER": "admin", "PASS": "secret"}
        result = resolve_secrets("${USER}:${PASS}", secrets)
        assert result == "admin:secret"

    def test_resolve_in_dict(self) -> None:
        """Test resolving secrets in a dict."""
        secrets = {"TOKEN": "abc123"}
        data = {"auth": {"token": "${TOKEN}"}}
        result = resolve_secrets(data, secrets)
        assert result["auth"]["token"] == "abc123"

    def test_resolve_in_list(self) -> None:
        """Test resolving secrets in a list."""
        secrets = {"A": "1", "B": "2"}
        data = ["${A}", "${B}"]
        result = resolve_secrets(data, secrets)
        assert result == ["1", "2"]

    def test_missing_secret_raises(self) -> None:
        """Test missing secret raises ValueError."""
        secrets: dict[str, str] = {}
        with pytest.raises(ValueError) as exc_info:
            resolve_secrets("${MISSING}", secrets)
        assert "MISSING" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_error_message_helpful(self) -> None:
        """Test error message includes fix instructions."""
        secrets: dict[str, str] = {}
        with pytest.raises(ValueError) as exc_info:
            resolve_secrets("${MY_SECRET}", secrets)
        error_msg = str(exc_info.value)
        assert "MY_SECRET=your_value" in error_msg
        assert "export MY_SECRET" in error_msg

    def test_non_string_passthrough(self) -> None:
        """Test non-string values pass through unchanged."""
        secrets: dict[str, str] = {}
        assert resolve_secrets(123, secrets) == 123
        assert resolve_secrets(True, secrets) is True
        assert resolve_secrets(None, secrets) is None

    def test_nested_structure(self) -> None:
        """Test resolving deeply nested structure."""
        secrets = {"KEY": "value"}
        data = {
            "level1": {
                "level2": {
                    "level3": ["${KEY}"],
                },
            },
        }
        result = resolve_secrets(data, secrets)
        assert result["level1"]["level2"]["level3"][0] == "value"

    def test_partial_string(self) -> None:
        """Test partial string substitution."""
        secrets = {"HOST": "localhost", "PORT": "5432"}
        result = resolve_secrets("postgres://${HOST}:${PORT}/db", secrets)
        assert result == "postgres://localhost:5432/db"
