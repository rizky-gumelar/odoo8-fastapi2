from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import date

# Schema untuk data yang dimasukkan saat membuat appointment line
class AppointmentLineCreate(BaseModel):
    # appointment_id: int 
    product_id: int 
    qty: float

class AppointmentLineUpdate(BaseModel):
    id: int
    product_id: int 
    qty: float

# Schema untuk data output setelah appointment line berhasil dibaca dari Odoo
class AppointmentLineOut(BaseModel):
    id: int
    product_id: int 
    qty: float

# Schema untuk data output setelah appointment line berhasil dibaca dari Odoo
# class AppointmentLineOutID(BaseModel):
#     id: int
#     product_id: int 
#     qty: float