from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date
from schemas.vehicle_head_schema import VehicleHeadOut
from schemas.vehicle_location_schema import VehicleLocationOut

class VehicleFleetBase(BaseModel):
    nopol: str = Field(..., title="Nomor Polisi")

class VehicleFleetCreate(VehicleFleetBase):
    head_id: Optional[int] = None
    last_location_id: Optional[int] = None

class VehicleFleetOut(VehicleFleetBase):
    id: int
    head: Optional[int]
    last_location: Optional[int]

class VehicleFleetOutDetail(VehicleFleetBase):
    id: int
    head: Optional[VehicleHeadOut] = None
    last_location: Optional[VehicleLocationOut] = None