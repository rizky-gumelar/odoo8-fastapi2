from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, List
from datetime import date
from schemas.vehicle_fleet_schema import VehicleFleetCreate, VehicleFleetOut
from schemas.vehicle_location_schema import VehicleLocationCreate, VehicleLocationOut
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data, normalize_relations
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
            # "address": result["last_location_id"][1],
        } if result.get("last_location_id") else None,
    }

@router.post("/location/", response_model=VehicleLocationOut)
def create_location(data: VehicleLocationCreate, user=Depends(get_odoo_user)):
    location_model = OdooModel("vehicle.location", user["uid"], user["username"], user["password"])
    fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])

    data_dict = preprocess_odoo_data(data.dict()) # process data
    
    fleet_id = data_dict.get("fleet_id")
    fleet_exists = fleet_model.search([("id", "=", fleet_id)], limit=1)
    if not fleet_exists:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    new_id = location_model.create(data_dict)
    location = location_model.read([new_id], fields=['id', 'fleet_id', 'latitude', 'longitude', 'address', 'village', 'district', 'city', 'province', 'postcode', 'timestamp'])
    # Normalisasi hasil
    clean_location = normalize_relations(location[0])
    return clean_location
