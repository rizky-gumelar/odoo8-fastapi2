from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, List
from datetime import date
from schemas.patient_schema import PatientBase, PatientCreate, PatientUpdate, PatientOut, PatientOutAll
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data
import base64

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/", response_model=List[PatientOutAll])
async def get_patients(user=Depends(get_odoo_user)):
    patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])
    result = patient_model.search_read(fields=['id', 'name', 'date_of_birth', 'gender', 'is_minor', 'guardian', 'tag_ids', 'image_small'], limit=50)
    return result

@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, user=Depends(get_odoo_user)):
    patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])

    # Gunakan read untuk ambil detail berdasarkan ID
    result = patient_model.read([patient_id], fields=['id', 'name', 'date_of_birth', 'gender', 'is_minor', 'guardian', 'tag_ids', 'image'])

    if not result:
        raise HTTPException(status_code=404, detail="Patient not found")

    return result[0]

# @router.post("/", response_model=PatientOut)
# def create_patient(data: PatientCreate, user=Depends(get_odoo_user)):
#     patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])
#     data_dict = preprocess_odoo_data(data.dict()) # process data
#     new_id = patient_model.create(data_dict)
#     patient = patient_model.read([new_id], fields=['id', 'name', 'date_of_birth', 'gender', 'is_minor', 'guardian', 'tag_ids'])
#     # Normalisasi hasil
#     # clean_patient = normalize_relations(patient[0])
#     return patient[0]

# CREATE
@router.post("/", response_model=PatientOut)
async def create_patient(
    name: str = Form(...),
    date_of_birth: Optional[date] = Form(None),
    gender: Optional[str] = Form(None),
    is_minor: Optional[bool] = Form(False),
    guardian: Optional[str] = Form(None),
    tag_ids: Optional[List[int]] = Form([]),
    image: Optional[UploadFile] = File(None),
    user=Depends(get_odoo_user)
):

    patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])

    # Proses image
    image_base64 = None
    if image:
        content = await image.read()
        image_base64 = base64.b64encode(content).decode("utf-8")

    # Siapkan dict data
    data_dict = {
        "name": name,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "is_minor": is_minor,
        "guardian": guardian,
        "tag_ids": [(6, 0, tag_ids)] if tag_ids else [],
    }
    data_dict = preprocess_odoo_data(data_dict)

    if image_base64:
        data_dict["image"] = image_base64

    # Proses ke Odoo
    new_id = patient_model.create(data_dict)
    patient = patient_model.read([new_id], fields=[
        'id', 'name', 'date_of_birth', 'gender', 'is_minor', 'guardian', 'tag_ids', 'image'
    ])
    
    return patient[0]

# @router.put("/{patient_id}", response_model=PatientOut)
# def update_patient(patient_id: int, data: PatientUpdate, user=Depends(get_odoo_user)):
#     patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])
#     data_dict = preprocess_odoo_data(data.dict()) # process data
#     updated = patient_model.write([patient_id], data_dict)
#     if not updated:
#         raise HTTPException(status_code=400, detail="Update failed")
#     patient = patient_model.read([patient_id], fields=['id', 'name', 'date_of_birth', 'gender', 'is_minor', 'guardian', 'tag_ids'])
#     return patient[0]

@router.put("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: int,
    name: Optional[str] = Form(None),
    date_of_birth: Optional[date] = Form(None),
    gender: Optional[str] = Form(None),
    is_minor: Optional[bool] = Form(None),
    guardian: Optional[str] = Form(None),
    tag_ids: Optional[List[int]] = Form(None),
    image: Optional[UploadFile] = File(None),
    user=Depends(get_odoo_user)
):
    # Siapkan koneksi Odoo
    patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])

    # Bangun data dict
    data_dict = {}
    if name is not None:
        data_dict["name"] = name
    if date_of_birth is not None:
        data_dict["date_of_birth"] = date_of_birth
    if gender is not None:
        data_dict["gender"] = gender
    if is_minor is not None:
        data_dict["is_minor"] = is_minor
    if guardian is not None:
        data_dict["guardian"] = guardian
    if tag_ids is not None:
        data_dict["tag_ids"] = [(6, 0, tag_ids)]

    if image:
        content = await image.read()
        image_base64 = base64.b64encode(content).decode("utf-8")
        data_dict["image"] = image_base64

    # Update ke Odoo
    if data_dict:
        patient_model.write([patient_id], data_dict)

    # Ambil data yang sudah di-update
    patient = patient_model.read([patient_id], fields=[
        'id', 'name', 'date_of_birth', 'gender', 'is_minor', 'guardian', 'tag_ids', 'image'
    ])

    return patient[0]

@router.delete("/{patient_id}")
def delete_patient(patient_id: int, user=Depends(get_odoo_user)):
    patient_model = OdooModel("hospital.patient", user["uid"], user["username"], user["password"])
    deleted = patient_model.unlink([patient_id])
    if not deleted:
        raise HTTPException(status_code=400, detail="Delete failed")
    return {"message": f"patient {patient_id} deleted successfully"}
