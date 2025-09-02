from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date

class VehicleHeadBase(BaseModel):
    nolambung: str = Field(..., title="Nomor Lambung")

class VehicleHeadCreate(VehicleHeadBase):
    pass

class VehicleHeadOut(VehicleHeadBase):
    id: int