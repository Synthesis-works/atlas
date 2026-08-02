from datetime import datetime

from pydantic import BaseModel


class SystemHealthDTO(BaseModel):
    status: str
    timestamp: datetime
    service: str


class VersionInfoDTO(BaseModel):
    service: str
    version: str
