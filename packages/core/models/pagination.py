from pydantic import BaseModel, ConfigDict
from typing import List, TypeVar, Generic

T = TypeVar('T')

class PaginatedResponseDTO(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    
    model_config = ConfigDict(from_attributes=True)
