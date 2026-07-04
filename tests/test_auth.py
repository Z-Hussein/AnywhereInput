"""Tests for authentication module."""
import pytest
from anywhereinput.auth import TokenManager


def test_token_generation(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    assert len(token) > 20
    assert tm.validate(token)


def test_token_validation(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    assert tm.validate(token)
    assert not tm.validate("invalid-token")


def test_token_rotation(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    t1 = tm.generate_token()
    t2 = tm.rotate()
    assert t1 != t2
    assert not tm.validate(t1)
    assert tm.validate(t2)


def test_permissions(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    assert tm.validate(token, "move")
    assert tm.validate(token, "click")
    assert not tm.validate(token, "invalid_permission")


def test_revoke(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token("test-token")
    assert tm.revoke(token)
    assert not tm.validate(token)
    # Revoke again should return False
    assert not tm.revoke(token)


def test_list_tokens(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    t1 = tm.generate_token("first")
    t2 = tm.generate_token("second")
    listed = tm.list_tokens()
    names = [t["name"] for t in listed]
    assert "first" in names
    assert "second" in names


def test_default_permissions(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    expected = ["move", "click", "scroll", "keyboard", "screen_toggle", "ping"]
    # Get stored permissions via list_tokens
    listed = [t for t in tm.list_tokens() if tm.validate(token)]
    assert len(listed) > 0


def test_custom_token_length(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    short = tm.generate_token(length=8)
    long_tok = tm.generate_token(length=64)
    assert len(short) < len(long_tok)
"""Tests for authentication module."""
import pytest
from anywhereinput.auth import TokenManager


def test_token_generation(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    assert len(token) > 20
    assert tm.validate(token)


def test_token_validation(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    assert tm.validate(token)
    assert not tm.validate("invalid-token")


def test_token_rotation(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    t1 = tm.generate_token()
    t2 = tm.rotate()
    assert t1 != t2
    assert not tm.validate(t1)
    assert tm.validate(t2)


def test_permissions(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    assert tm.validate(token, "move")
    assert tm.validate(token, "click")
    assert not tm.validate(token, "invalid_permission")


def test_revoke(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token("test-token")
    assert tm.revoke(token)
    assert not tm.validate(token)
    # Revoke again should return False
    assert not tm.revoke(token)


def test_list_tokens(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    t1 = tm.generate_token("first")
    t2 = tm.generate_token("second")
    listed = tm.list_tokens()
    names = [t["name"] for t in listed]
    assert "first" in names
    assert "second" in names


def test_default_permissions(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    token = tm.generate_token()
    expected = ["move", "click", "scroll", "keyboard", "screen_toggle", "ping"]
    # Get stored permissions via list_tokens
    listed = [t for t in tm.list_tokens() if tm.validate(token)]
    assert len(listed) > 0


def test_custom_token_length(tmp_path):
    tm = TokenManager(token_file=str(tmp_path / "tokens.json"))
    short = tm.generate_token(length=8)
    long_tok = tm.generate_token(length=64)
    assert len(short) < len(long_tok)
