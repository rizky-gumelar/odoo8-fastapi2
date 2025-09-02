from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date

class VehicleFleetBase(BaseModel):
    nopol: str = Field(..., title="Nomor Polisi")

class VehicleFleetCreate(VehicleFleetBase):
    head_id: Optional[int] = None
    last_location_id: Optional[int] = None

class VehicleFleetOut(VehicleFleetBase):
    id: int
    head: Optional[VehicleHeadRead] = None
    last_location: Optional[VehicleLocationRead] = None