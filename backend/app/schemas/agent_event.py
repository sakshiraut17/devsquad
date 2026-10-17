"""Pydantic V2 schemas for Agent events and telemetry."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentEvent(BaseModel):
    """Telemetry event logged during agent execution."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    agent_name: str
    event_type: str
    message: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime
