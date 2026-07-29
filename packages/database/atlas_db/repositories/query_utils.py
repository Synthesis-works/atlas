from typing import Any

from sqlalchemy.orm import Query


def apply_pagination(query: Query, limit: int, offset: int | None = None) -> Query:
    """
    Applies limit and offset to a SQLAlchemy Query.
    """
    query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    return query


def apply_sorting(query: Query, model: type, sort_field: str | None, order: str) -> Query:
    """
    Applies sorting to a SQLAlchemy Query based on a model field.
    Returns the query unmodified if the field does not exist.
    """
    if not sort_field:
        return query

    field_attr = getattr(model, sort_field, None)
    if field_attr is None:
        return query

    if order.lower() == "asc":
        return query.order_by(field_attr.asc())
    else:
        return query.order_by(field_attr.desc())


def get_paginated_results(
    query: Query, limit: int, offset: int | None = None
) -> tuple[list[Any], int]:
    """
    Returns the total count and the paginated results for a given query.
    """
    total = query.count()
    paginated_query = apply_pagination(query, limit, offset)
    return paginated_query.all(), total
