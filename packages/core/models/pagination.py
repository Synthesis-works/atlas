from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponseDTO(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int

    model_config = ConfigDict(from_attributes=True)
