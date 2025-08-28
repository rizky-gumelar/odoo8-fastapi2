from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date

class PatientBase(BaseModel):
    name: str = Field(..., example="Jane Doe")
    date_of_birth: Optional[date] = Field(None)
    gender: Optional[str] = Field(None, example="female")
    is_minor: Optional[bool] = Field(False)
    guardian: Optional[str] = Field(None)
    tag_ids: Optional[List[int]] = Field(default_factory=list)
    # image: Optional[str] = Field(None, description="Base64-encoded image")
    # image_medium: Optional[str] = Field(None, description="Base64-encoded image")

# tidak jadi dipakai
class PatientCreate(PatientBase):
    pass

# tidak jadi dipakai
class PatientUpdate(BaseModel):
    name: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str] = Field(None, example="male")
    is_minor: Optional[bool]
    guardian: Optional[str]
    tag_ids: Optional[List[int]]

class PatientOut(PatientBase):
    id: int
    image: Optional[str] = Field(None, description="Base64-encoded image")

    @field_validator("guardian", "image", mode="before")
    @classmethod
    def clean_fields(cls, v):
        if v is False:
            return None
        if isinstance(v, str):
            return v.replace('\n', '')  # Hapus newline dari base64
        return v

class PatientOutAll(PatientBase):
    id: int
    # image: Optional[str] = Field(None, description="Base64-encoded image")
    image_small: Optional[str] = Field(None, description="Base64-encoded image")

    @field_validator("guardian", "image_small", mode="before")
    @classmethod
    def clean_fields(cls, v):
        if v is False:
            return None
        if isinstance(v, str):
            return v.replace('\n', '')  # Hapus newline dari base64
        return v