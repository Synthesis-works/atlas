from datetime import datetime
import uuid
from typing import Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from atlas_db.core.base import Base

class OutboxMessage(Base):
    __tablename__ = 'outbox_messages'

    outbox_message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    aggregate_type = Column(String(255), nullable=False)
    
    event_type = Column(String(255), nullable=False)
    event_version = Column(Integer, nullable=False, default=1)
    schema_version = Column(Integer, nullable=False, default=1)
    
    payload = Column(JSONB, nullable=False)
    trace_context = Column(JSONB, nullable=True)
    
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, PROCESSING, PROCESSED, FAILED, DEAD_LETTER
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
