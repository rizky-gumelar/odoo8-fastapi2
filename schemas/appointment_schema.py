from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import date
from schemas.appointment_line_schema import AppointmentLineCreate, AppointmentLineOut, AppointmentLineUpdate

# Schema untuk data yang dimasukkan saat membuat appointment
class AppointmentCreate(BaseModel):
    reference: Optional[str] = "New"
    patient_id: int  # ID dari hospital.patient (Many2one)
    date_appointment: Optional[date]
    note: Optional[str] = None
    state: Optional[str] = "draft"
    # appointment_line_ids: Optional[List[int]] = []  # ID appointment lines (One2many)
    appointment_line_ids: Optional[List[AppointmentLineCreate]]
    display_name: Optional[str]
    total_qty: float
    date_of_birth: Optional[date]

# Schema untuk data output setelah appointment berhasil dibaca dari Odoo
class AppointmentOut(BaseModel):
    id: int
    reference: str
    patient_id: Optional[int]  # ID dari hospital.patient
    date_appointment: Optional[date]
    note: Optional[str]
    state: str
    # appointment_line_ids: List[int]  # Daftar ID appointment line
    appointment_line_ids: List[AppointmentLineOut]
    display_name: Optional[str]
    total_qty: float
    date_of_birth: Optional[date]

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def convert_false_to_none(cls, v):
        return None if v is False else v

class AppointmentOut2(BaseModel):
    id: int
    # reference: str
    patient_id: Optional[int]  # ID dari hospital.patient
    date_appointment: Optional[date]
    note: Optional[str]
    state: str
    # appointment_line_ids: List[int]  # Daftar ID appointment line
    appointment_line_ids: List[AppointmentLineOut]
    display_name: Optional[str]
    total_qty: float
    date_of_birth: Optional[date]

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def convert_false_to_none(cls, v):
        return None if v is False else v

class AppointmentUpdate(BaseModel):
    # reference: Optional[str] = None
    patient_id: Optional[int] = None
    date_appointment: Optional[date] = None
    note: Optional[str] = None
    state: Optional[str] = None
    appointment_line_ids: Optional[List[AppointmentLineUpdate]] = None
    display_name: Optional[str] = None
    total_qty: Optional[float] = None
    date_of_birth: Optional[date] = None

class AppointmentStateUpdate(BaseModel):
    state: str