from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse


def offset(page: int, per_page: int) -> int:
    """SQL offset for a given page / per_page."""
    return (max(page, 1) - 1) * per_page


def _meta(page: int, per_page: int, total: int) -> Dict[str, Any]:
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "next_page": (page + 1) if page < pages else None,
        "prev_page": (page - 1) if page > 1 else None,
    }


class Response:
    """Standard JSON envelope.

    Plain:
        return Response(success=True, message="OK", data={}, request=request)

    Paginated:
        return Response(success=True, data=items, page=page, per_page=per_page, total=total, request=request)
    """

    def __new__(
        cls,
        success: bool,
        message: str = "",
        error: str = "",
        data: Any = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        total: Optional[int] = None,
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> JSONResponse:
        if status_code is not None and not (100 <= status_code <= 599):
            raise ValueError("status_code must be between 100 and 599")

        sc = status_code if status_code is not None else (
            status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )

        payload: Dict[str, Any] = {"success": bool(success)}
        if message:
            payload["message"] = message
        if error:
            payload["error"] = error

        if data is not None:
            try:
                payload["data"] = jsonable_encoder(data)
            except Exception:
                payload["data"] = data.model_dump(exclude_none=True) if hasattr(data, "model_dump") else str(data)

        if page is not None and per_page is not None and total is not None:
            payload["meta"] = _meta(int(page), int(per_page), int(total))

        rid = request_id or (getattr(request.state, "request_id", None) if request else None) or secrets.token_hex(8)
        payload["request_id"] = rid
        payload["timestamp"] = datetime.now(timezone.utc).isoformat() + "Z"

        if sc == status.HTTP_204_NO_CONTENT:
            return StarletteResponse(status_code=sc)

        return JSONResponse(status_code=sc, content={k: v for k, v in payload.items() if v is not None})
