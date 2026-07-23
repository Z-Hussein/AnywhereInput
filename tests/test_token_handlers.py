"""Tests for server token handlers."""

import json
from unittest import mock

import pytest

from anywhereinput.server._token_handlers import TokenAPI


def _make_request(method="GET", path="/api/tokens", body=None, match_info=None):
    req = mock.MagicMock()
    req.method = method
    req.path = path
    req.match_info = match_info or {}
    req.headers = {"Content-Type": "application/json"}
    if body is not None:
        req.json = mock.AsyncMock(return_value=json.loads(body) if isinstance(body, str) else body)
    else:
        req.json = mock.AsyncMock(return_value={})
    req.read = mock.AsyncMock(return_value=b"{}")
    return req


@pytest.fixture
def token_api():
    srv = mock.MagicMock()
    srv.token_manager.tokens = {
        "abc123full": {"name": "test", "permissions": ["screen"], "created": "2026-01-01"}
    }
    srv.token_manager.DEFAULT_PERMISSIONS.return_value = ["screen"]
    srv.token_manager.revoke.return_value = True
    srv.token_manager.generate_token.return_value = "newtoken1234567890abcdef"
    srv._get_client_ip.return_value = ("127.0.0.1", 12345)
    srv.clients = []
    srv.clients_lock = mock.AsyncMock()
    srv._client_tokens = {}
    srv._client_meta = {}
    return TokenAPI(srv)


class TestListTokens:
    @pytest.mark.asyncio
    async def test_returns_tokens(self, token_api):
        req = _make_request()
        resp = await token_api.list_tokens(req)
        assert resp.status == 200


class TestCreateToken:
    @pytest.mark.asyncio
    async def test_valid(self, token_api):
        token_api._srv.token_manager.generate_token.return_value = "newtoken123"
        body = json.dumps({"name": "newtok"})
        req = _make_request(method="POST", body=body)
        resp = await token_api.create_token(req)
        assert resp.status == 201

    @pytest.mark.asyncio
    async def test_invalid_json(self, token_api):
        req = _make_request(method="POST")
        req.json = mock.AsyncMock(side_effect=json.JSONDecodeError("", "", 0))
        resp = await token_api.create_token(req)
        # create_token catches JSON errors and defaults to empty body, still creates token
        assert resp.status == 201


class TestRevokeToken:
    @pytest.mark.asyncio
    async def test_found(self, token_api):
        req = _make_request(method="DELETE", match_info={"token_id": "abc123full"})
        resp = await token_api.revoke_token(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_not_found(self, token_api):
        token_api._srv.token_manager.revoke.return_value = False
        req = _make_request(method="DELETE", match_info={"token_id": "none"})
        resp = await token_api.revoke_token(req)
        assert resp.status == 404


class TestUpdateToken:
    @pytest.mark.asyncio
    async def test_found(self, token_api):
        body = json.dumps({"name": "updated"})
        req = _make_request(method="PATCH", match_info={"token_id": "abc123full"}, body=body)
        resp = await token_api.update_token(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_not_found(self, token_api):
        body = json.dumps({"name": "x"})
        req = _make_request(method="PATCH", match_info={"token_id": "none"}, body=body)
        resp = await token_api.update_token(req)
        assert resp.status == 404


class TestListClients:
    @pytest.mark.asyncio
    async def test_empty(self, token_api):
        req = _make_request()
        resp = await token_api.list_clients(req)
        assert resp.status == 200
