"""Tests for server request handlers."""

import json
from unittest import mock

import pytest

from anywhereinput.server._request_handlers import RequestAPI


def _make_request(method="GET", path="/api/requests", body=None, match_info=None):
    req = mock.MagicMock()
    req.method = method
    req.path = path
    req.match_info = match_info or {}
    req.headers = {"Content-Type": "application/json"}
    if body is not None:
        req.json = mock.AsyncMock(return_value=json.loads(body) if isinstance(body, (str, bytes)) else body)
    else:
        req.json = mock.AsyncMock(return_value={})
    req.read = mock.AsyncMock(return_value=b"{}")
    return req


@pytest.fixture
def request_api():
    srv = mock.MagicMock()
    srv.token_manager.generate_token.return_value = "autotoken123"
    srv._get_client_ip.return_value = ("127.0.0.1", 12345)
    return RequestAPI(srv)


class TestRequestConnect:
    @pytest.mark.asyncio
    async def test_valid(self, request_api):
        body = json.dumps({"client_name": "phone", "permissions": ["screen"]})
        req = _make_request(method="POST", body=body)
        resp = await request_api.request_connect(req)
        assert resp.status == 201

    @pytest.mark.asyncio
    async def test_empty_name(self, request_api):
        body = json.dumps({"client_name": ""})
        req = _make_request(method="POST", body=body)
        resp = await request_api.request_connect(req)
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_invalid_json(self, request_api):
        req = _make_request(method="POST")
        req.json = mock.AsyncMock(side_effect=json.JSONDecodeError("", "", 0))
        resp = await request_api.request_connect(req)
        assert resp.status == 400


class TestListRequests:
    @pytest.mark.asyncio
    async def test_empty(self, request_api):
        req = _make_request()
        resp = await request_api.list_requests(req)
        assert resp.status == 200


class TestApproveRequest:
    @pytest.mark.asyncio
    async def test_not_found(self, request_api):
        req = _make_request(method="PATCH", match_info={"id": "nonexistent"})
        resp = await request_api.approve_request(req)
        assert resp.status == 404


class TestDeclineRequest:
    @pytest.mark.asyncio
    async def test_not_found(self, request_api):
        req = _make_request(method="PATCH", match_info={"id": "nonexistent"})
        resp = await request_api.decline_request(req)
        assert resp.status == 404


class TestCheckStatus:
    @pytest.mark.asyncio
    async def test_not_found(self, request_api):
        req = _make_request(method="GET", match_info={"id": "nonexistent"})
        resp = await request_api.check_request_status(req)
        assert resp.status == 404
