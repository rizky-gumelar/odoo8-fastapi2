from fastapi import APIRouter, Depends, HTTPException
from typing import List
from schemas.appointment_line_schema import AppointmentLineCreate, AppointmentLineOut
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data, normalize_relations

router = APIRouter(prefix="/appointment_line", tags=["Appointment Line"])

# Endpoint untuk membuat Appointment Line
@router.post("/", response_model=AppointmentLineOut)
def create_appointment_line(data: AppointmentLineCreate, user=Depends(get_odoo_user)):
    appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])
    
    # Persiapkan data untuk pembuatan appointment line
    data_dict = {
        'appointment_id': data.appointment_id,
        'product_id': data.product_id,
        'qty': data.qty
    }
    
    # Buat appointment line baru
    new_id = appointment_line_model.create(data_dict)
    
    # Ambil data appointment line yang baru dibuat
    appointment_line = appointment_line_model.read([new_id], fields=[
        'id', 'appointment_id', 'product_id', 'qty'
    ])

    # Normalize relations (like patient_id, appointment_line_ids)
    clean_appointment = normalize_relations(appointment_line[0])
    
    return clean_appointment

# Endpoint untuk membaca Appointment Line berdasarkan ID
@router.get("/{line_id}", response_model=AppointmentLineOut)
def get_appointment_line(line_id: int, user=Depends(get_odoo_user)):
    appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])
    
    # Cari appointment line berdasarkan ID
    appointment_line = appointment_line_model.read([line_id], fields=[
        'id', 'appointment_id', 'product_id', 'qty'
    ])
    
    if not appointment_line:
        raise HTTPException(status_code=404, detail="Appointment line not found")
    
    clean_appointment_line = normalize_relations(appointment_line[0])
    return clean_appointment_line

# Endpoint untuk mendapatkan semua Appointment Lines yang terkait dengan Appointment tertentu
@router.get("/appointment/{appointment_id}", response_model=List[AppointmentLineOut])
def get_appointment_lines(appointment_id: int, user=Depends(get_odoo_user)):
    appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])
    
    # Cari semua appointment lines yang terkait dengan appointment_id
    appointment_lines = appointment_line_model.search_read(
        domain=[('appointment_id', '=', appointment_id)], 
        fields=['id', 'appointment_id', 'product_id', 'qty']
    )
    
    clean_appointment_lines = [normalize_relations(appointment_line) for appointment_line in appointment_lines]
    return clean_appointment_lines

@router.put("/{appointment_line_id}", response_model=AppointmentLineOut)
def update_appointment(appointment_line_id: int, data: AppointmentLineCreate, user=Depends(get_odoo_user)):
    appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])

    # Preprocess data
    preprocessed_data = preprocess_odoo_data(data.dict()) # process data

    # Update appointment in Odoo
    appointment_line_model.write([appointment_line_id], preprocessed_data)

    # Get updated appointment data from Odoo
    appointment_lines = appointment_line_model.read([appointment_line_id], 
        fields=['id', 'appointment_id', 'product_id', 'qty'])

    # Normalize relations
    clean_appointment = normalize_relations(appointment_lines[0])

    return clean_appointment

@router.delete("/{appointment_line_id}", status_code=204)
def delete_appointment(appointment_line_id: int, user=Depends(get_odoo_user)):
    appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])

    # Delete the appointment
    result = appointment_line_model.unlink([appointment_line_id])

    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"message": "Appointment deleted successfully"}
