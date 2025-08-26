from fastapi import APIRouter, Depends, HTTPException
from schemas.partner_schema import PartnerCreate, PartnerResponse
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from typing import List

router = APIRouter(prefix="/partners", tags=["Partners"])

@router.get("/", response_model=List[PartnerResponse])
def get_partners(user=Depends(get_odoo_user)):
    partner_model = OdooModel("res.partner", user["uid"], user["username"], user["password"])
    result = partner_model.search_read(fields=["id", "name", "email", "phone"], limit=50)
    return result

@router.post("/", response_model=PartnerResponse)
def create_partner(data: PartnerCreate, user=Depends(get_odoo_user)):
    partner_model = OdooModel("res.partner", user["uid"], user["username"], user["password"])
    new_id = partner_model.create(data.dict())
    partner = partner_model.read([new_id], fields=["id", "name", "email", "phone"])
    return partner[0]

@router.put("/{partner_id}", response_model=PartnerResponse)
def update_partner(partner_id: int, data: PartnerCreate, user=Depends(get_odoo_user)):
    partner_model = OdooModel("res.partner", user["uid"], user["username"], user["password"])
    updated = partner_model.write([partner_id], data.dict())
    if not updated:
        raise HTTPException(status_code=400, detail="Update failed")
    partner = partner_model.read([partner_id], fields=["id", "name", "email", "phone"])
    return partner[0]

@router.delete("/{partner_id}")
def delete_partner(partner_id: int, user=Depends(get_odoo_user)):
    partner_model = OdooModel("res.partner", user["uid"], user["username"], user["password"])
    deleted = partner_model.unlink([partner_id])
    if not deleted:
        raise HTTPException(status_code=400, detail="Delete failed")
    return {"message": f"Partner {partner_id} deleted successfully"}
