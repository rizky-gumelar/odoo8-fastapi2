from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, List
from datetime import date
from schemas.patient_schema import PatientBase, PatientCreate, PatientUpdate, PatientOut, PatientOutAll
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data
import base64

router = APIRouter(prefix="/vehicle", tags=["Vehicle"])

@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, user=Depends(get_odoo_user)):
    patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])

    # Gunakan read untuk ambil detail berdasarkan ID
    result = patient_model.read([patient_id], fields=['id', 'name', 'date_of_birth', 'gender', 'is_minor', 'guardian', 'tag_ids', 'image'])

    if not result:
        raise HTTPException(status_code=404, detail="Patient not found")

    return result[0]
