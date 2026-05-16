"""Custom Tortoise fields for PostgreSQL-specific types.

`VectorField` 는 PGVector 확장의 `vector(N)` 컬럼을 매핑한다.
aerich 가 DDL 생성 시 SQL_TYPE 을 이용하므로 마이그레이션도 자동 생성된다.
런타임 직렬화는 pgvector.asyncpg.register_vector 가 처리한다.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from tortoise.fields.base import Field


class VectorField(Field[list[float]]):
    """PGVector `vector(dimensions)` 컬럼."""

    SQL_TYPE = "vector"
    indexable = False

    def __init__(self, dimensions: int = 768, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.dimensions = dimensions
        self.SQL_TYPE = f"vector({dimensions})"

    def to_db_value(self, value: Sequence[float] | None, instance: Any) -> list[float] | None:
        if value is None:
            return None
        return [float(v) for v in value]

    def to_python_value(self, value: Any) -> list[float] | None:
        if value is None:
            return None
        return [float(v) for v in value]
