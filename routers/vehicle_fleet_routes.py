from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, List
from datetime import date
from schemas.vehicle_fleet_schema import VehicleFleetCreate, VehicleFleetOut
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data
import base64

router = APIRouter(prefix="/vehicle", tags=["Vehicle"])

@router.get("/{nopol}", response_model=VehicleFleetOut)
def get_fleet(nopol: str, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])

    # cari ID berdasarkan nopol
    fleet_ids = fleet_model.search([('nopol', '=', nopol)], limit=1)

    if not fleet_ids:
        raise HTTPException(status_code=404, detail="Fleet not found")
    result = fleet_model.read(fleet_ids, fields=['id', 'nopol', 'head_id', 'last_location_id'])[0]

    return {
        "id": result["id"],
        "nopol": result["nopol"],
        "head": {
            "id": result["head_id"][0],
            "nolambung": result["head_id"][1],
        } if result.get("head_id") else None,
        "last_location": {
            "id": result["last_location_id"][0],
            "address": result["last_location_id"][1],
        } if result.get("last_location_id") else None,
    }
