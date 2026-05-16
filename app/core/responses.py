"""ORJSONResponse 확장: Decimal / date / datetime / UUID 등 비 JSON 타입을 안전하게 직렬화."""

from __future__ import annotations

import datetime as _dt
import decimal
import uuid
from typing import Any

import orjson
from starlette.responses import JSONResponse


def _default(obj: Any) -> Any:
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, _dt.date | _dt.datetime | _dt.time):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, set | frozenset):
        return list(obj)
    raise TypeError(f"Type is not JSON serializable: {type(obj).__name__}")


class ORJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content,
            default=_default,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_NAIVE_UTC,
        )
