from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from schemas.vehicle_head_schema import VehicleHeadOut
from schemas.vehicle_location_schema import VehicleLocationOut, VehicleLocationBase

class VehicleKarloBase(BaseModel):
    gps_imei: str = Field(..., example="No IMEI GPS")
    gps_vendor: str = Field(..., example="Brand or Vendor GPS")
    gps_network: str = Field(..., example="2G / 4G")
    plate_number: str = Field(..., example="H-1234-OH")
    latitude: float = Field(..., example=-7.32086666666667)
    longitude: float = Field(..., example=112.716716666667)
    altitude: float = Field(..., example=0.0)
    bearing: float = Field(..., example=0.0)
    speed: float = Field(..., example=30.0)
    battery: float = Field(..., example=50.0)
    lastUpdated: datetime = Field(..., example="2022-02-24T21:17:49.524Z")

class VehicleKarloCreate(VehicleKarloBase):
    pass

class VehicleKarloOut(VehicleLocationBase):
    # id: int
    head: Optional[VehicleHeadOut] = None
