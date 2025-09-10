from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date


class VehicleLocationBase(BaseModel):
    gpslatitude: Optional[float] = None
    gpslongitude: Optional[float] = None
    gpsstreet: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    gpscity: Optional[str] = None
    # province: Optional[str] = None
    gpspostcode: Optional[str] = None
    gpstime: Optional[datetime] = None

class VehicleLocationCreate(VehicleLocationBase):
    fleet_id: int

class VehicleLocationOut(VehicleLocationBase):
    id: int
    fleet_id: int

    @field_validator("gpsstreet", "kelurahan", "kecamatan", "gpscity", "gpspostcode", mode="before")
    @classmethod
    def convert_false_to_none(cls, v):
        return None if v is False else v