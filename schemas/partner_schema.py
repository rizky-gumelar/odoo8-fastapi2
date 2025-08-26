from pydantic import BaseModel, field_validator
from typing import Optional

class PartnerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class PartnerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("email", "phone", mode="before")
    @classmethod
    def convert_false_to_none(cls, v):
        return None if v is False else v
