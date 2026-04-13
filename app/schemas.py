from datetime import datetime
from pydantic import BaseModel
from app.models import DeviceStatus, AlertSeverity


# Device
class DeviceCreate(BaseModel):
    name: str
    type: str
    location: str | None = None


class DeviceStatusUpdate(BaseModel):
    status: DeviceStatus


class DeviceResponse(BaseModel):
    id: int
    name: str
    type: str
    location: str | None
    status: DeviceStatus
    created_at: datetime

    model_config = {"from_attributes": True}


# Metric


class MetricCreate(BaseModel):
    key: str
    value: float
    unit: str | None = None


class MetricResponse(BaseModel):
    id: int
    device_id: int
    key: str
    value: float
    unit: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


# Alert


class AlertResponse(BaseModel):
    id: int
    device_id: int
    severity: AlertSeverity
    message: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
