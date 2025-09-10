from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, List
from datetime import date
from schemas.vehicle_fleet_schema import VehicleFleetCreate, VehicleFleetOut, VehicleFleetOutDetail
from schemas.vehicle_location_schema import VehicleLocationCreate, VehicleLocationOut
from schemas.vehicle_karlo_schema import VehicleKarloCreate, VehicleKarloOut
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data, normalize_relations
import base64
import httpx
from fastapi.concurrency import run_in_threadpool
import asyncio

odoo_rpc_semaphore = asyncio.Semaphore(20)

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

@router.get("/{policenumber}")
def get_fleet(policenumber: str, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])

    # fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])
    # location_model = OdooModel("vehicle.location", user["uid"], user["username"], user["password"])

    # cari ID berdasarkan policenumber
    fleet_ids = fleet_model.search([('policenumber', '=', policenumber)], limit=1)

    if not fleet_ids:
        raise HTTPException(status_code=404, detail="Fleet not found")
    result = fleet_model.read(fleet_ids, fields=['id', 'policenumber', 'head_id', 'gps_locations'])[0]

    # Head
    head = None
    if result.get("head_id"):
        head = {
            "id": result["head_id"][0],
            "nolambung": result["head_id"][1],
        }

    # Last Location
    last_location = None
    if result.get("gps_locations"):
        loc_data = location_model.read(
            [result["gps_locations"][0]],
            fields=['id', 'fleet_id', 'gpslatitude', 'gpslongitude', 'gpsstreet', 'kelurahan', 'kecamatan', 'gpscity', 'gpspostcode', 'gpstime']
        )
        if loc_data:
            loc = loc_data[0]
            last_location = {
                "id": loc["id"],
                "fleet_id": loc["fleet_id"][0] if isinstance(loc["fleet_id"], list) else loc["fleet_id"],
                "gpslatitude": loc.get("gpslatitude"),
                "gpslongitude": loc.get("gpslongitude"),
                "gpsstreet": loc.get("gpsstreet"),
                "kelurahan": loc.get("kelurahan"), 
                "kecamatan": loc.get("kecamatan"),
                "gpscity": loc.get("gpscity"),
                # "province": loc.get("province"),
                "gpspostcode": loc.get("gpspostcode"),
                "gpstime": loc.get("gpstime"),
            }

    return {
        "id": result["id"],
        "policenumber": result["policenumber"],
        "head": head,
        "last_location": last_location,
    }

@router.post("/location/")
def create_location(data: VehicleLocationCreate, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])

    # fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])
    # location_model = OdooModel("vehicle.location", user["uid"], user["username"], user["password"])

    data_dict = preprocess_odoo_data(data.dict()) # process data
    
    fleet_id = data_dict.get("fleet_id")
    fleet_exists = fleet_model.search([("id", "=", fleet_id)], limit=1)
    if not fleet_exists:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    new_id = location_model.create(data_dict)
    location = location_model.read([new_id], fields=['id', 'fleet_id', 'gpslatitude', 'gpslongitude', 'gpsstreet', 'kelurahan', 'kecamatan', 'gpscity', 'gpspostcode', 'gpstime'])
    # Normalisasi hasil
    clean_location = normalize_relations(location[0])
    return clean_location

@router.get("/area/{postcode}")
def get_area(postcode: str, user=Depends(get_odoo_user)):
    kelurahan_model = OdooModel("sisu.karlo.master.kelurahan", user["uid"], user["username"], user["password"])
    provinsi_model = OdooModel("sisu.karlo.master.provinsi", user["uid"], user["username"], user["password"])

    kelurahan_id = kelurahan_model.search([('kodepos', '=', postcode)], limit=1)
    if not kelurahan_id:
        raise HTTPException(status_code=404, detail="Postcode not found")

    kelurahan = kelurahan_model.read(kelurahan_id, fields=['id', 'name', 'kecamatan_id', 'city_id', 'provinsi_id'])[0]

    # Ubah provinsi_id dari [id, name] menjadi dict
    prov_id, prov_name = kelurahan.get("provinsi_id") or (None, None)
    # kelurahan["provinsi_id"] = {"id": prov_id, "name": prov_name} if prov_id else None

    provinsi = provinsi_model.read([prov_id], fields=['id', 'name', 'area'])[0] if prov_id else {}

    return {
        "kelurahan_data": kelurahan,
        "provinsi_data": provinsi
    }

@router.post("/karlo-update/")
async def update_location(data: VehicleKarloCreate, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])
    kelurahan_model = OdooModel("sisu.karlo.master.kelurahan", user["uid"], user["username"], user["password"])
    provinsi_model = OdooModel("sisu.karlo.master.provinsi", user["uid"], user["username"], user["password"])
    # fleet_model = OdooModel("vehicle.fleet", user["uid"], user["username"], user["password"])
    # location_model = OdooModel("vehicle.location", user["uid"], user["username"], user["password"])

    data_dict = preprocess_odoo_data(data.dict()) # process data
    # cari ID berdasarkan nopol
    nopol = data_dict.get("plate_number")
    # fleet_id = fleet_model.search([('nopol', '=', nopol)], limit=1)
    # fleet_id = await run_in_threadpool(fleet_model.search, [('nopol', '=', nopol)], limit=1)
    fleet_id = await safe_run_in_threadpool(fleet_model.search, [('policenumber', '=', nopol)], limit=1)

    if not fleet_id:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    # get address
    address_data = await get_address_from_coordinates(data.dict())
    address_line = address_data.get("address", {})

    #get area
    kelurahan_id = kelurahan_model.search([('kodepos', '=', address_line.get("postcode"))], limit=1)
    kelurahan = kelurahan_model.read(kelurahan_id, fields=['id', 'name', 'kecamatan_id', 'city_id', 'provinsi_id'])[0]
    prov_id, prov_name = kelurahan.get("provinsi_id") or (None, None)
    provinsi = provinsi_model.read([prov_id], fields=['id', 'name', 'area'])[0] if prov_id else {}

    # save location
    new_location = {
        "gpslatitude": data_dict.get("latitude"),
        "gpslongitude": data_dict.get("longitude"),
        "gpsstreet": address_data.get("display_name") or address_line.get("road") or "",
        "kelurahan": address_line.get("village") or address_line.get("hamlet") or address_line.get("neighbourhood") or address_line.get("residential") or "",
        "kecamatan": address_line.get("state_district") or address_line.get("city_district") or address_line.get("suburb") or "",
        "gpscity": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        "gpskota": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        # "gps_area": address_line.get("state") or address_line.get("region") or address_line.get("county") or "",
        "gpspostcode": address_line.get("postcode") or "",
        "gpstime": data_dict.get("lastUpdated"),
        "gps_area": provinsi.get("area"),
        "fleet_id": fleet_id[0]
    }
    # new_id = location_model.create(new_location)
    # new_id = await run_in_threadpool(location_model.create, new_location)
    new_id = await safe_run_in_threadpool(location_model.create, new_location)
        
    return {
        "status": "200 OK", 
        "nopol": nopol,
        "timestamp": data_dict.get("lastUpdated")
        }
    # return new_location 

@router.post("/karlo-update2/")
async def update_location2(data: VehicleKarloCreate, user=Depends(get_odoo_user)):
    # Inisialisasi model Odoo
    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])
    kelurahan_model = OdooModel("sisu.karlo.master.kelurahan", user["uid"], user["username"], user["password"])
    provinsi_model = OdooModel("sisu.karlo.master.provinsi", user["uid"], user["username"], user["password"])
    
    # Preprocess data
    data_dict = preprocess_odoo_data(data.dict())
    nopol = data_dict.get("plate_number")

    # Jalankan search dan get_address secara paralel
    search_task = asyncio.create_task(
        # run_in_threadpool(fleet_model.search, [('nopol', '=', nopol)], limit=1)
        safe_run_in_threadpool(fleet_model.search, [('policenumber', '=', nopol)], limit=1)
    )
    address_task = asyncio.create_task(
        get_address_from_coordinates(data.dict())
    )

    # Tunggu dua-duanya selesai
    fleet_id, address_data = await asyncio.gather(search_task, address_task)

    # Validasi hasil search
    if not fleet_id:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    address_line = address_data.get("address", {})

    #get area
    #get area
    kelurahan_id = kelurahan_model.search([('kodepos', '=', address_line.get("postcode"))], limit=1)
    kelurahan = kelurahan_model.read(kelurahan_id, fields=['id', 'name', 'kecamatan_id', 'city_id', 'provinsi_id'])[0]
    prov_id, prov_name = kelurahan.get("provinsi_id") or (None, None)
    provinsi = provinsi_model.read([prov_id], fields=['id', 'name', 'area'])[0] if prov_id else {}

    # Siapkan data lokasi
    new_location = {
        "gpslatitude": data_dict.get("latitude"),
        "gpslongitude": data_dict.get("longitude"),
        "gpsstreet": address_data.get("display_name") or address_line.get("road") or "",
        "kelurahan": address_line.get("village") or address_line.get("hamlet") or address_line.get("neighbourhood") or address_line.get("residential") or "",
        "kecamatan": address_line.get("state_district") or address_line.get("city_district") or address_line.get("suburb") or "",
        "gpscity": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        "gpskota": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        # "gps_area": address_line.get("state") or address_line.get("region") or address_line.get("county") or "",
        "gpspostcode": address_line.get("postcode") or "",
        "gpstime": data_dict.get("lastUpdated"),
        "gps_area": provinsi.get("area"),
        "fleet_id": fleet_id[0]
    }

    # Simpan data lokasi (juga di threadpool)
    # new_id = await run_in_threadpool(location_model.create, new_location)
    new_id = await safe_run_in_threadpool(location_model.create, new_location)

    return {
        "status": "200 OK",
        "nopol": nopol,
        "timestamp": data_dict.get("lastUpdated")
    }

