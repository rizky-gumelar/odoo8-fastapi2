from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date

class VehicleLocationBase(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    vilage: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postcode: Optional[str] = None
    timestamp: Optional[datetime] = None

class VehicleLocationCreate(VehicleLocationBase):
    fleet_id: int

class VehicleLocationOut(VehicleLocationBase):
    id: int
    fleet_id: int