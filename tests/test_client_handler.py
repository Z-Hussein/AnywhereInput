"""Tests for the ClientHandler (serves static files)."""
import pytest
from pathlib import Path
from anywhereinput.client import ClientHandler


@pytest.fixture
def handler():
    return ClientHandler()


def test_handler_init_default(handler):
    assert handler.static_dir.exists()


def test_index_file_exists(handler):
    index_file = handler.static_dir / "client.html"
    assert index_file.exists()
    content = index_file.read_text(encoding="utf-8")
    assert len(content) > 100


def test_static_css_exists(handler):
    css_file = handler.static_dir / "style.css"
    assert css_file.exists()


def test_static_js_exists(handler):
    js_file = handler.static_dir / "app.js"
    assert js_file.exists()


def test_index_content_not_empty(handler):
    index_file = handler.static_dir / "client.html"
    content = index_file.read_text(encoding="utf-8")
    assert len(content) > 1000
    assert "<html" in content.lower() or "<!doctype" in content.lower()


def test_all_static_files_present(handler):
    expected = ["client.html", "app.js", "style.css"]
    for fname in expected:
        fpath = handler.static_dir / fname
        assert fpath.exists(), f"{fname} not found in {handler.static_dir}"
