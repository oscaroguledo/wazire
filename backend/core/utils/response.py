from typing import Any, Dict, Optional, Sequence, Tuple, Type

from fastapi.responses import JSONResponse
from starlette import status
from starlette.responses import Response as StarletteResponse
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from starlette.requests import Request


def _build_pagination(
	page: int,
	per_page: int,
	total: int,
	base_url: Optional[str] = None,
	extra_params: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Optional[str]]]]:
	"""Create standardized pagination payload and optional links.

	Validates inputs and returns a dict in the agreed shape:

	{
	  "page": int,
	  "per_page": int,
	  "total": int,
	  "pages": int,
	  "has_next": bool,
	  "has_prev": bool,
	  "next_page": int|null,
	  "prev_page": int|null,
	  "links": {"self": str, "next": str|null, "prev": str|null}  # optional
	}
	"""
	try:
		page = int(page)
		per_page = int(per_page)
		total = int(total)
	except Exception:
		raise ValueError("page, per_page and total must be integers")

	if page < 1:
		raise ValueError("page must be >= 1")
	if per_page < 1:
		raise ValueError("per_page must be >= 1")
	if total < 0:
		raise ValueError("total must be >= 0")

	pages = (total + per_page - 1) // per_page if per_page else 1
	if pages < 1:
		pages = 1

	next_page = page + 1 if page < pages else None
	prev_page = page - 1 if page > 1 else None

	pagination = {
		"page": page,
		"per_page": per_page,
		"total": total,
		"pages": pages,
		"has_next": next_page is not None,
		"has_prev": prev_page is not None,
		"next_page": next_page,
		"prev_page": prev_page,
	}

	links = None
	if base_url:
		# build robust links preserving existing querystring and extra_params
		parts = urlparse(base_url)
		base_qs = dict(parse_qsl(parts.query, keep_blank_values=True))

		def _build_url(p: Optional[int]) -> Optional[str]:
			if p is None:
				return None
			qs = dict(base_qs)  # copy
			if extra_params:
				qs.update({k: str(v) for k, v in extra_params.items()})
			qs.update({"page": str(p), "per_page": str(per_page)})
			new_q = urlencode(qs)
			new_parts = parts._replace(query=new_q)
			return urlunparse(new_parts)

		links = {"self": _build_url(page), "next": _build_url(next_page), "prev": _build_url(prev_page)}

	# return meta and links separately (links may be None)
	return pagination, links


class ErrorObject(BaseModel):
	type: Optional[str] = None
	title: Optional[str] = None
	status: Optional[int] = None
	detail: Optional[str] = None
	instance: Optional[str] = None


class _ResponseSchema(BaseModel):
	success: bool
	message: Optional[str] = None
	# error can be a plain string or RFC7807-style object
	error: Optional[Any] = None
	data: Optional[Any] = None
	meta: Optional[Dict[str, Any]] = None
	links: Optional[Dict[str, Optional[str]]] = None
	request_id: str
	timestamp: str


# Typed models for OpenAPI use
class MetaModel(BaseModel):
	page: int
	per_page: int
	total: int
	pages: int
	has_next: bool
	has_prev: bool
	next_page: Optional[int] = None
	prev_page: Optional[int] = None


class LinksModel(BaseModel):
	self: str
	next: Optional[str] = None
	prev: Optional[str] = None


class ResponseModel(BaseModel):
	success: bool
	message: Optional[str] = None
	error: Optional[Any] = None
	data: Optional[Any] = None
	meta: Optional[MetaModel] = None
	links: Optional[LinksModel] = None
	request_id: str
	timestamp: str


class Response:
	"""Simple, standard response envelope.

	Constructor returns a Starlette JSONResponse so `return Response(...)` works directly
	in FastAPI route handlers.

	Example:
		return Response(True, message="OK", data={})
		return Response(False, error="Bad request", status_code=400)
	"""

	pass


	def __new__(
		cls,
		success: bool,
		message: str = "",
		error: str = "",
		data: Any = None,
		pagination: Optional[dict] = None,
		data_model: Optional[Type[BaseModel]] = None,
		request: Optional[Request] = None,
		request_id: Optional[str] = None,
		status_code: Optional[int] = None,
	) -> JSONResponse:
		# Allow callers to provide any valid HTTP status code (100-599).
		if status_code is not None:
			if not isinstance(status_code, int) or not (100 <= status_code <= 599):
				raise ValueError("status_code must be an int between 100 and 599")
			sc = status_code
		else:
			sc = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST

		# build base payload, omitting empty fields
		payload: Dict[str, Any] = {"success": bool(success)}
		if message:
			payload["message"] = message
		if error:
			payload["error"] = error
		if data is not None:
			# Optionally validate nested `data` against a provided Pydantic model
			if data_model is not None:
				try:
					validated_data = data_model.model_validate(data)
					# replace with serialized dict to ensure consistency
					payload["data"] = validated_data.model_dump(exclude_none=True)
				except Exception as e:
					# surface validation error clearly
					return JSONResponse(
						status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
						content={
							"success": False,
							"error": f"Response data validation failed: {str(e)}",
							"request_id": rid if (rid := (request_id or (getattr(request.state, 'request_id', None)))) else secrets.token_hex(8),
							"timestamp": datetime.now(timezone.utc).isoformat() + "Z",
						},
					)
			else:
				# Ensure data is JSON serializable (handles UUID, datetime, Pydantic models, etc.)
				try:
					payload["data"] = jsonable_encoder(data)
				except Exception:
					# Fallback: attempt Pydantic model dump if possible
					if hasattr(data, "model_dump"):
						try:
							payload["data"] = data.model_dump(exclude_none=True)
						except Exception:
							payload["data"] = str(data)
					else:
						payload["data"] = str(data)

		# pagination/meta handling: callers should prefer passing a validated meta dict
		if pagination is not None:
			if isinstance(pagination, dict):
				meta = pagination
				links = None
			else:
				try:
					pg, pp, tot, base = pagination
				except Exception:
					raise ValueError("pagination must be a dict or (page, per_page, total, base_url)")
				meta, links = _build_pagination(pg, pp, tot, base)

			if meta:
				payload["meta"] = meta
			if links:
				payload["links"] = links

		# tracing metadata: prefer explicit request_id, then Request.state, then generated
		rid = None
		if request_id:
			rid = request_id
		elif request is not None:
			rid = getattr(request.state, "request_id", None)
		if not rid:
			rid = secrets.token_hex(8)
		payload["request_id"] = rid
		payload["timestamp"] = datetime.now(timezone.utc).isoformat() + "Z"

		# runtime validate payload against pydantic model for OpenAPI consistency
		try:
			validated = _ResponseSchema(**payload)
			# exclude None fields so `meta`/`links` are omitted when absent
			content = validated.model_dump(exclude_none=True)
		except Exception as e:
			# If validation fails, raise to surface the problem during development
			raise

		# 204 No Content: return an empty Starlette Response
		if sc == status.HTTP_204_NO_CONTENT:
			return StarletteResponse(status_code=sc)

		return JSONResponse(status_code=sc, content=content)

# how to use it
# return Response(success=True, message="Data retrieved", data={"foo": "bar"})
# return Response(success=False, error="Invalid input", status_code=422)
# return Response(success=True, message="Data retrieved", data={"foo": "bar"}, pagination=(1, 10, 100, "https://api.example.com/data"))
#  make sure it wokrs for every use case, including pagination:

