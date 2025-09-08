from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from schemas.vehicle_head_schema import VehicleHeadOut

class VehicleFleetBase(BaseModel):
    policenumber: str = Field(..., title="Nomor Polisi")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postcode: Optional[str] = None
    timestamp: Optional[datetime] = None

class VehicleFleetCreate(VehicleFleetBase):
    head_id: Optional[int] = None

class VehicleFleetOut(VehicleFleetBase):
    id: int
    head_id: Optional[int]

class VehicleFleetOutDetail(VehicleFleetBase):
    id: int
    head: Optional[VehicleHeadOut] = None

    @field_validator("timestamp","address", "village", "district", "city", "province", "postcode", mode="before")
    @classmethod
    def convert_false_to_none(cls, v):
        return None if v is False else v