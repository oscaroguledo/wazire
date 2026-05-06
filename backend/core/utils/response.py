from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette import status
from starlette.responses import Response as StarletteResponse


class Response:
    """Minimal JSON response envelope.

    Keeps a very small, predictable shape:
        {"success": bool, "message": str?, "error": str?, "data": any?, "pagination": dict?}

    Note: `request` and legacy args are accepted by callers but ignored here to keep callsites simple.
    """

    def __new__(
        cls,
        success: bool,
        message: str = "",
        error: str = "",
        data: Any = None,
        pagination: Optional[dict] = None,
        # keep these for callsite compatibility but ignore their values
        *_,
        status_code: Optional[int] = None,
        **__,
    ) -> JSONResponse:
        if status_code is not None:
            if not isinstance(status_code, int) or not (100 <= status_code <= 599):
                raise ValueError("status_code must be an int between 100 and 599")
            sc = status_code
        else:
            sc = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST

        payload: Dict[str, Any] = {"success": bool(success)}
        if message:
            payload["message"] = message
        if error:
            payload["error"] = error

        if data is not None:
            try:
                payload["data"] = jsonable_encoder(data)
            except Exception:
                payload["data"] = str(data)

        if pagination is not None:
            payload["pagination"] = pagination

        # 204 No Content: return an empty Starlette Response
        if sc == status.HTTP_204_NO_CONTENT:
            return StarletteResponse(status_code=sc)

        return JSONResponse(status_code=sc, content=payload)
