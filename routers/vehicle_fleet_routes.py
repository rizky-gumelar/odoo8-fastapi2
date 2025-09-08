from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, List
from datetime import date
from schemas.vehicle_fleet_schema import VehicleFleetCreate, VehicleFleetOut, VehicleFleetOutDetail
from schemas.vehicle_karlo_schema import VehicleKarloCreate
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data, normalize_relations
import base64
import httpx
from fastapi.concurrency import run_in_threadpool
import asyncio

odoo_rpc_semaphore = asyncio.Semaphore(4)

async def safe_run_in_threadpool(func, *args, **kwargs):
    async with odoo_rpc_semaphore:
        return await run_in_threadpool(func, *args, **kwargs)

async def get_address_from_coordinates(data: dict):
    lat = data.get("latitude")
    lon = data.get("longitude")

    if lat is None or lon is None:
        return None  # atau raise error

    url = "https://app-nominatim.sibasurya.com/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2"
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        return None

# ##############################################
router = APIRouter(prefix="/vehicle", tags=["Vehicle"])

@router.get("/{nopol}", response_model=VehicleFleetOutDetail)
def get_fleet(nopol: str, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])

    # cari ID berdasarkan nopol
    fleet_id = fleet_model.search([('nopol', '=', nopol)], limit=1)

    if not fleet_id:
        raise HTTPException(status_code=404, detail="Fleet not found")
    result = fleet_model.read(fleet_id, fields=['id', 'nopol', 'latitude', 'longitude', 'address', 'village', 'district', 'province', 'postcode', 'head_id', 'city', 'timestamp'])[0]

    # Head
    head = None
    if result.get("head_id"):
        head = {
            "id": result["head_id"][0],
            "nolambung": result["head_id"][1],
        }
    result["head"] = head
    return result

@router.post("/karlo-update/")
async def update_location(data: VehicleKarloCreate, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])

    data_dict = preprocess_odoo_data(data.dict()) # process data
    # cari ID berdasarkan nopol
    nopol = data_dict.get("plate_number")
    # fleet_id = fleet_model.search([('nopol', '=', nopol)], limit=1)
    # fleet_id = await run_in_threadpool(fleet_model.search, [('nopol', '=', nopol)], limit=1)
    fleet_id = await safe_run_in_threadpool(fleet_model.search, [('nopol', '=', nopol)], limit=1)


    if not fleet_id:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    # get address
    address_data = await get_address_from_coordinates(data.dict())
    address_line = address_data.get("address", {})
    # save location
    new_location = {
        "latitude": data_dict.get("latitude"),
        "longitude": data_dict.get("longitude"),
        "address": address_data.get("display_name") or address_line.get("road") or "",
        "village": address_line.get("village") or address_line.get("hamlet") or address_line.get("neighbourhood") or address_line.get("residential") or "",
        "district": address_line.get("state_district") or address_line.get("city_district") or address_line.get("suburb") or "",
        "city": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        "province": address_line.get("state") or address_line.get("region") or address_line.get("county") or "",
        "postcode": address_line.get("postcode") or "",
        "timestamp": data_dict.get("lastUpdated"),
        "fleet_id": fleet_id[0]
    }
    # new_id = location_model.create(new_location)
    # new_id = await run_in_threadpool(location_model.create, new_location)
    new_id = await safe_run_in_threadpool(fleet_model.write, [fleet_id[0]], new_location)
        
    return {
        "status": "200 OK", 
        "nopol": nopol,
        "timestamp": data_dict.get("lastUpdated"),
        }
    # return new_location 

@router.post("/karlo-update2/")
async def update_location2(data: VehicleKarloCreate, user=Depends(get_odoo_user)):
    # Inisialisasi model Odoo
    fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])

    # Preprocess data
    data_dict = preprocess_odoo_data(data.dict())
    nopol = data_dict.get("plate_number")

    # Jalankan search dan get_address secara paralel
    search_task = asyncio.create_task(
        run_in_threadpool(fleet_model.search, [('nopol', '=', nopol)], limit=1)
    )
    address_task = asyncio.create_task(
        get_address_from_coordinates(data_dict)
    )

    # Tunggu dua-duanya selesai
    fleet_id, address_data = await asyncio.gather(search_task, address_task)

    # Validasi hasil search
    if not fleet_id:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    address_line = address_data.get("address", {})

    # Siapkan data lokasi
    new_location = {
        "latitude": data_dict.get("latitude"),
        "longitude": data_dict.get("longitude"),
        "address": address_data.get("display_name") or address_line.get("road") or "",
        "village": address_line.get("village") or address_line.get("hamlet") or address_line.get("neighbourhood") or address_line.get("residential") or "",
        "district": address_line.get("state_district") or address_line.get("city_district") or address_line.get("suburb") or "",
        "city": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        "province": address_line.get("state") or address_line.get("region") or address_line.get("county") or "",
        "postcode": address_line.get("postcode") or "",
        "timestamp": data_dict.get("lastUpdated"),
        "fleet_id": fleet_id[0]
    }

    # Simpan data lokasi (juga di threadpool)
    new_id = await safe_run_in_threadpool(fleet_model.write, [fleet_id[0]], new_location)

    return {
        "status": "200 OK",
        "nopol": nopol,
        "timestamp": data_dict.get("lastUpdated")
    }

