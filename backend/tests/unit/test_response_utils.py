"""Unit tests for core/utils/response.py."""
import pytest
from fastapi.responses import JSONResponse
from starlette.responses import Response as StarletteResponse

from core.utils.response import Response, offset, _meta


class TestOffset:
    def test_page_1_offset_is_zero(self):
        assert offset(1, 10) == 0

    def test_page_2_offset_is_per_page(self):
        assert offset(2, 10) == 10

    def test_page_3_offset(self):
        assert offset(3, 20) == 40

    def test_page_zero_treated_as_page_1(self):
        assert offset(0, 10) == 0


class TestMeta:
    def test_single_page(self):
        m = _meta(1, 10, 5)
        assert m["total"] == 5
        assert m["pages"] == 1
        assert m["has_next"] is False
        assert m["has_prev"] is False

    def test_multiple_pages(self):
        m = _meta(1, 10, 25)
        assert m["pages"] == 3
        assert m["has_next"] is True
        assert m["has_prev"] is False

    def test_last_page(self):
        m = _meta(3, 10, 25)
        assert m["has_next"] is False
        assert m["has_prev"] is True

    def test_zero_total(self):
        m = _meta(1, 10, 0)
        assert m["pages"] == 0
        assert m["has_next"] is False


class TestResponse:
    def test_success_response_returns_json(self):
        resp = Response(success=True, message="OK", data={"key": "value"})
        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 200

    def test_error_response_returns_400(self):
        resp = Response(success=False, error="Bad input")
        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 400

    def test_custom_status_code(self):
        resp = Response(success=True, status_code=201)
        assert resp.status_code == 201

    def test_204_returns_starlette_response(self):
        resp = Response(success=True, status_code=204)
        assert isinstance(resp, StarletteResponse)
        assert resp.status_code == 204

    def test_invalid_status_code_raises(self):
        with pytest.raises(ValueError):
            Response(success=True, status_code=999)

    def test_paginated_response_includes_meta(self):
        resp = Response(success=True, data=[1, 2, 3], page=1, per_page=10, total=3)
        import json
        body = json.loads(resp.body)
        assert "meta" in body
        assert body["meta"]["total"] == 3

    def test_request_id_included(self):
        resp = Response(success=True, request_id="test-id-123")
        import json
        body = json.loads(resp.body)
        assert body["request_id"] == "test-id-123"

    def test_data_none_included_when_success(self):
        resp = Response(success=True, data=None)
        import json
        body = json.loads(resp.body)
        assert "data" in body
        assert body["data"] is None
