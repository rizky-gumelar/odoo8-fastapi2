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
import time
from logger import logger

odoo_rpc_semaphore = asyncio.Semaphore(10)

async def safe_run_in_threadpool(func, *args, **kwargs):
    async with odoo_rpc_semaphore:
        return await run_in_threadpool(func, *args, **kwargs)

# NOMINATIM
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
        # Mengambil json dari response
        result = response.json()

        # Menyaring hanya key dan nilai yang diminta
        filtered_data = {
            "address": result.get("address"),
            "display_name": result.get("display_name"),
            "name": result.get("name"),
            "addresstype": result.get("type"),
            "lat": result.get("lat"),
            "lon": result.get("lon")
        }

        return filtered_data
    else:
        return None

# ##############################################
router = APIRouter(prefix="/vehicle", tags=["Vehicle"])

@router.get("/{policenumber}")
def get_fleet(policenumber: str, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])

    # cari ID berdasarkan policenumber
    fleet_ids = fleet_model.search([('policenumber', '=', policenumber)], limit=1)

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
async def create_location(data: VehicleLocationCreate, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])

    data_dict = preprocess_odoo_data(data.dict()) # process data
    
    fleet_id = data_dict.get("fleet_id")
    fleet_exists = fleet_model.search([("id", "=", fleet_id)], limit=1)
    if not fleet_exists:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    # Cek apakah data lokasi dengan fleet_id dan gpstime sudah ada
    existing_location_ids = await safe_run_in_threadpool(
        location_model.search,
        [
            ('fleet_id', '=', fleet_id)
        ],
        limit=1
    )

    if existing_location_ids:
        # Jika sudah ada, lakukan update
        updated = await safe_run_in_threadpool(
            location_model.write,
            existing_location_ids,
            data_dict
        )
        action = "updated"
        location_id = existing_location_ids[0]
    else:
        # Jika belum ada, buat baru
        location_id = await safe_run_in_threadpool(location_model.create, data_dict)
        action = "created"
    

    location = location_model.read([location_id], fields=['id', 'fleet_id', 'gpslatitude', 'gpslongitude', 'gpsstreet', 'kelurahan', 'kecamatan', 'gpscity', 'gpspostcode', 'gpstime'])
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

    kelurahan = kelurahan_model.read(kelurahan_id, fields=['id', 'kodepos', 'name', 'kecamatan', 'kabupaten', 'kecamatan_id', 'city_id', 'provinsi_id'])[0]

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

    data_dict = preprocess_odoo_data(data.dict()) # process data
    # cari ID berdasarkan nopol
    nopol = data_dict.get("plate_number")
    fleet_id = await safe_run_in_threadpool(fleet_model.search, [('policenumber', '=', nopol)], limit=1)

    # get address
    address_data = await get_address_from_coordinates(data.dict())
    address_line = address_data.get("address", {})

    # GET KELURAHAN ID BY POSTCODE DLL
    kelurahan_id = None
    postcode = address_line.get("postcode")
    kelurahan_name = (
        address_line.get("village")
        or address_line.get("hamlet")
        or address_line.get("neighbourhood")
        or address_line.get("residential")
    )
    kecamatan_name = (
        address_line.get("state_district")
        or address_line.get("city_district")
        or address_line.get("suburb")
    )
    city_name = (
        address_line.get("city")
        or address_line.get("town")
        or address_line.get("county")
        or address_line.get("municipality")
    )    
    province_name = (
        address_line.get("state")
        or address_line.get("region")
        or address_line.get("county")
    )
    # POSTCODE
    if postcode:
        kelurahan_id = await safe_run_in_threadpool(
            kelurahan_model.search,
            [('kodepos', '=', postcode)],
            limit=1
        )
    # KABUPATEN
    if not kelurahan_id and city_name:
        domain = [
            ('kabupaten', 'ilike', city_name),
        ]
        kelurahan_id = await safe_run_in_threadpool(
            kelurahan_model.search,
            domain,
            limit=1
        )
    # PROVINSI
    if not kelurahan_id and province_name:
        domain = [
            ('provinsi', 'ilike', province_name),
        ]
        kelurahan_id = await safe_run_in_threadpool(
            kelurahan_model.search,
            domain,
            limit=1
        )

    # GET KELURAHAN DATA
    kelurahan = {}
    if kelurahan_id:
        kelurahan_data = await safe_run_in_threadpool(
            kelurahan_model.read,
            kelurahan_id,
            fields=['id', 'name', 'kecamatan_id', 'city_id', 'provinsi_id']
        )
        if kelurahan_data:
            kelurahan = kelurahan_data[0]
            
    # GET AREA
    prov_id, prov_name = kelurahan.get("provinsi_id") or (None, None)
    provinsi = {}
    if prov_id:
        provinsi_data = await safe_run_in_threadpool(
            provinsi_model.read,
            [prov_id],
            fields=['id', 'name', 'area']
        )
        if provinsi_data:
            provinsi = provinsi_data[0]

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

    # UPSERT
    location_id = await safe_run_in_threadpool(location_model.create, new_location)
    action = "created"

    return {
        "status": "200 OK",
        "nopol": nopol,
        "action": action,
        "location_id": location_id,
        "timestamp": data_dict.get("lastUpdated")
    }

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
        safe_run_in_threadpool(fleet_model.search, [('policenumber', '=', nopol)], limit=1)
    )
    address_task = asyncio.create_task(
        get_address_from_coordinates(data.dict())
    )

    # Tunggu selesai
    fleet_id, address_data = await asyncio.gather(search_task, address_task)

    # Validasi hasil search
    if not fleet_id:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    address_line = address_data.get("address", {})

    # GET KELURAHAN ID BY POSTCODE DLL
    kelurahan_id = None
    postcode = address_line.get("postcode")
    kelurahan_name = (
        address_line.get("village")
        or address_line.get("hamlet")
        or address_line.get("neighbourhood")
        or address_line.get("residential")
    )
    kecamatan_name = (
        address_line.get("state_district")
        or address_line.get("city_district")
        or address_line.get("suburb")
    )
    city_name = (
        address_line.get("city")
        or address_line.get("town")
        or address_line.get("county")
        or address_line.get("municipality")
    )    
    province_name = (
        address_line.get("state")
        or address_line.get("region")
        or address_line.get("county")
    )
    # POSTCODE
    if postcode:
        kelurahan_id = await safe_run_in_threadpool(
            kelurahan_model.search,
            [('kodepos', '=', postcode)],
            limit=1
        )
    # KABUPATEN
    if not kelurahan_id and city_name:
        domain = [
            ('kabupaten', 'ilike', city_name),
        ]
        kelurahan_id = await safe_run_in_threadpool(
            kelurahan_model.search,
            domain,
            limit=1
        )
    # PROVINSI
    if not kelurahan_id and province_name:
        domain = [
            ('provinsi', 'ilike', province_name),
        ]
        kelurahan_id = await safe_run_in_threadpool(
            kelurahan_model.search,
            domain,
            limit=1
        )

    # GET KELURAHAN DATA
    kelurahan = {}
    if kelurahan_id:
        kelurahan_data = await safe_run_in_threadpool(
            kelurahan_model.read,
            kelurahan_id,
            fields=['id', 'name', 'kodepos', 'kecamatan', 'kabupaten', 'kecamatan_id', 'city_id', 'provinsi_id']
        )
        if kelurahan_data:
            kelurahan = kelurahan_data[0]
            
    # GET AREA DATA
    prov_id, prov_name = kelurahan.get("provinsi_id") or (None, None)
    provinsi = {}
    if prov_id:
        provinsi_data = await safe_run_in_threadpool(
            provinsi_model.read,
            [prov_id],
            fields=['id', 'name', 'area']
        )
        if provinsi_data:
            provinsi = provinsi_data[0]

    # Siapkan data lokasi
    new_location = {
        "gpslatitude": data_dict.get("latitude"),
        "gpslongitude": data_dict.get("longitude"),
        "gpsstreet": address_data.get("display_name") or address_line.get("road") or "",
        # "kelurahan": address_line.get("village") or address_line.get("hamlet") or address_line.get("neighbourhood") or address_line.get("residential") or "",
        # "kecamatan": address_line.get("state_district") or address_line.get("city_district") or address_line.get("suburb") or "",
        # "gpscity": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        # "gpskota": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        # "gps_area": address_line.get("state") or address_line.get("region") or address_line.get("county") or "",
        # "gpspostcode": address_line.get("postcode") or "",
        "gpstime": data_dict.get("lastUpdated"),
        "kelurahan": kelurahan.get("name"),
        "kecamatan": kelurahan.get("kecamatan"),
        "gpskota": kelurahan.get("kabupaten"),
        "gpspostcode": kelurahan.get("kodepos"),
        "gpscity": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
        "gps_area": provinsi.get("area"),
        "fleet_id": fleet_id[0]
    }

    # UPSERT
    location_id = await safe_run_in_threadpool(location_model.create, new_location)

    return {
        "status": "200 OK",
        "nopol": nopol,
        "location_id": location_id,
        "timestamp": data_dict.get("lastUpdated")
    }

# SIMPLIFY VIA ODOO
@router.post("/karlo-update3/")
async def update_location3(data: VehicleKarloCreate, user=Depends(get_odoo_user)):

    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])

    data_dict = preprocess_odoo_data(data.dict())
    result = await run_in_threadpool(
        fleet_model.call,
        "karlo_update_location",  # nama method
        [data_dict]  # argumen untuk method
    )
    
    return result

@router.post("/karlo-update5/")
async def update_location5(data: VehicleKarloCreate, user=Depends(get_odoo_user)):

    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])

    data_dict = preprocess_odoo_data(data.dict())
    address_data = await get_address_from_coordinates(data.dict())
    data_dict["address_data"] = address_data

    result = await safe_run_in_threadpool(
        fleet_model.call,
        "karlo_update_location2",  # nama method
        [data_dict]  # argumen untuk method
    )
    
    return result

# @router.post("/karlo-update4/")
# async def update_location4(data: VehicleKarloCreate, user=Depends(get_odoo_user)):

#     fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    
#     # Preprocess data
#     # data_dict = preprocess_odoo_data(data.dict())
#     nopol = data.dict().get("plate_number")

#     # Jalankan search dan get_address secara paralel
#     search_task = asyncio.create_task(
#         # run_in_threadpool(fleet_model.search, [('nopol', '=', nopol)], limit=1)
#         safe_run_in_threadpool(fleet_model.search, [('policenumber', '=', nopol)], limit=1)
#     )
#     address_task = asyncio.create_task(
#         get_address_from_coordinates(data.dict())
#     )
#     # Tunggu dua-duanya selesai
#     fleet_id, address_data = await asyncio.gather(search_task, address_task)

#     # Validasi hasil search
#     if not fleet_id:
#         raise HTTPException(status_code=404, detail="Fleet ID not found")

#     address_data["latitude"] = data.latitude
#     address_data["longitude"] = data.longitude
#     address_data["lastUpdated"] = data.lastUpdated
#     data_dict = preprocess_odoo_data(address_data)

#     print(data_dict)
#     try:
#         # 3. Panggil method 'update_location_from_api' pada record fleet yang ditemukan
#         #    Gunakan execute_kw untuk memanggil method pada record tertentu dengan argumen.
#         print("Fleet ID to be used:", fleet_id)
#         result = await run_in_threadpool(
#             fleet_model.call2,
#             "update_location_from_api",   # Nama method di model Odoo
#             fleet_id[0],                 # ID record fleet dalam bentuk list
#             data_dict # argumen untuk method
#         )
        
#         # 4. Kembalikan response dari Odoo secara langsung
#         return result

#     except Exception as e:
#         # Menangani kemungkinan error dari Odoo (misal: UserError)
#         raise HTTPException(status_code=500, detail=f"An error occurred in Odoo: {str(e)}")

########### BENCHMARK ###########
# @router.post("/karlo-update/")
# async def update_location(data: VehicleKarloCreate, user=Depends(get_odoo_user)):
#     total_start = time.time()

#     # Inisialisasi Odoo model
#     fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
#     location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])
#     kelurahan_model = OdooModel("sisu.karlo.master.kelurahan", user["uid"], user["username"], user["password"])
#     provinsi_model = OdooModel("sisu.karlo.master.provinsi", user["uid"], user["username"], user["password"])

#     data_dict = preprocess_odoo_data(data.dict())
#     nopol = data_dict.get("plate_number")

#     # ⏱️ Durasi pencarian fleet
#     fleet_search_start = time.time()
#     fleet_id = await safe_run_in_threadpool(fleet_model.search, [('policenumber', '=', nopol)], limit=1)
#     fleet_search_duration = time.time() - fleet_search_start
#     logger.info(f"🚗 Fleet Search duration: {fleet_search_duration:.3f} seconds")

#     # ⏱️ Durasi pencarian alamat
#     address_search_start = time.time()
#     address_data = await get_address_from_coordinates(data.dict())
#     address_line = address_data.get("address", {})
#     address_search_duration = time.time() - address_search_start
#     logger.info(f"📍 Address Search duration: {address_search_duration:.3f} seconds")

#     # ⏱️ Mulai waktu simpan lokasi
#     save_start = time.time()

#     new_location = {
#         "gpslatitude": data_dict.get("latitude"),
#         "gpslongitude": data_dict.get("longitude"),
#         "gpsstreet": address_data.get("display_name") or address_line.get("road") or "",
#         "kelurahan": address_line.get("village") or address_line.get("hamlet") or address_line.get("neighbourhood") or address_line.get("residential") or "",
#         "kecamatan": address_line.get("state_district") or address_line.get("city_district") or address_line.get("suburb") or "",
#         "gpscity": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
#         "gpskota": address_line.get("city") or address_line.get("town") or address_line.get("county") or address_line.get("municipality") or "",
#         "gps_area": address_line.get("state") or address_line.get("region") or address_line.get("county") or "",
#         "gpspostcode": address_line.get("postcode") or "",
#         "gpstime": data_dict.get("lastUpdated"),
#         "fleet_id": fleet_id[0]
#     }

#     existing_location_ids = await safe_run_in_threadpool(
#         location_model.search,
#         [('fleet_id', '=', fleet_id[0])],
#         limit=1
#     )

#     if existing_location_ids:
#         updated = await run_in_threadpool(
#             location_model.write,
#             existing_location_ids,
#             new_location
#         )
#         action = "updated"
#         location_id = existing_location_ids[0]
#     else:
#         location_id = await run_in_threadpool(location_model.create, new_location)
#         action = "created"

#     save_duration = time.time() - save_start
#     logger.info(f"💾 Save/Update Location duration: {save_duration:.3f} seconds")

#     total_duration = time.time() - total_start
#     logger.info(f"✅ Total Endpoint Duration: {total_duration:.3f} seconds")

#     return {
#         "status": "200 OK",
#         "nopol": nopol,
#         "action": action,
#         "location_id": location_id,
#         "timestamp": data_dict.get("lastUpdated")
#     }

@router.post("/karlo-update4/")
async def update_location4(data: VehicleKarloCreate, user=Depends(get_odoo_user)):

    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    nopol = data.dict().get("plate_number")

    search_task = asyncio.create_task(
        safe_run_in_threadpool(fleet_model.search, [('policenumber', '=', nopol)], limit=1)
    )
    address_task = asyncio.create_task(
        get_address_from_coordinates(data.dict())
    )
    fleet_id, address_data = await asyncio.gather(search_task, address_task)

    if not fleet_id:
        raise HTTPException(status_code=404, detail="Fleet ID not found")

    # Persiapan data
    address_data["latitude"] = data.latitude
    address_data["longitude"] = data.longitude
    address_data["lastUpdated"] = data.lastUpdated
    data_dict = preprocess_odoo_data(address_data)

    # print(f"Data dict sebelum dikirim ke Odoo: {data_dict}")
    # RPC update call LEMPAR KE ODOO
    result = await run_in_threadpool(
        fleet_model.call2,
        "update_location_from_api",
        fleet_id,
        data_dict
    )

    return result

########### CLOSE BENCHMARK ###########

# @router.get("/2/{policenumber}")
# def get_fleet(policenumber: str, user=Depends(get_odoo_user)):
#     fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
#     location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])

#     # Cari ID fleet berdasarkan policenumber
#     fleet_ids = fleet_model.search([('policenumber', '=', policenumber)], limit=1)

#     if not fleet_ids:
#         raise HTTPException(status_code=404, detail="Fleet not found")
    
#     result = fleet_model.read(fleet_ids, fields=['id', 'policenumber', 'head_id', 'gps_locations'])[0]

#     # Head info
#     head = None
#     if result.get("head_id"):
#         head = {
#             "id": result["head_id"][0],
#             "nolambung": result["head_id"][1],
#         }

#     # All Locations
#     locations = []
#     gps_location_ids = result.get("gps_locations", [])
#     if gps_location_ids:
#         loc_data = location_model.read(
#             gps_location_ids,
#             fields=['id', 'fleet_id', 'gpslatitude', 'gpslongitude', 'gpsstreet', 'kelurahan', 'kecamatan', 'gpscity', 'gpspostcode', 'gpstime']
#         )
#         for loc in loc_data:
#             locations.append({
#                 "id": loc["id"],
#                 "fleet_id": loc["fleet_id"][0] if isinstance(loc["fleet_id"], list) else loc["fleet_id"],
#                 "gpslatitude": loc.get("gpslatitude"),
#                 "gpslongitude": loc.get("gpslongitude"),
#                 "gpsstreet": loc.get("gpsstreet"),
#                 "kelurahan": loc.get("kelurahan"),
#                 "kecamatan": loc.get("kecamatan"),
#                 "gpscity": loc.get("gpscity"),
#                 "gpspostcode": loc.get("gpspostcode"),
#                 "gpstime": loc.get("gpstime"),
#             })

#     # Ambil lokasi terakhir (jika kamu masih ingin tetap mengirimkan last_location terpisah)
#     last_location = locations[-1] if locations else None

#     return {
#         "id": result["id"],
#         "policenumber": result["policenumber"],
#         "head": head,
#         "last_location": last_location,
#         "locations": locations  # Tambahkan list semua lokasi
#     }

@router.delete("/{policenumber}/locations")
def delete_all_locations(policenumber: str, user=Depends(get_odoo_user)):
    fleet_model = OdooModel("sisu.karlo.master.fleet", user["uid"], user["username"], user["password"])
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])

    # Cari fleet berdasarkan nomor polisi
    fleet_ids = fleet_model.search([('policenumber', '=', policenumber)], limit=1)
    if not fleet_ids:
        raise HTTPException(status_code=404, detail="Fleet not found")

    fleet = fleet_model.read(fleet_ids, fields=["gps_locations"])[0]
    gps_location_ids = fleet.get("gps_locations", [])

    if not gps_location_ids:
        return {"message": "No GPS locations to delete."}

    # Hapus semua GPS locations
    deleted = location_model.unlink(gps_location_ids)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete GPS locations")

    return {
        "message": f"Successfully deleted {len(gps_location_ids)} GPS locations for policenumber '{policenumber}'"
    }

@router.delete("/deleteall-location")
def delete_all_locations(user=Depends(get_odoo_user)):
    location_model = OdooModel("sisu.karlo.master.fleet.gpslocation", user["uid"], user["username"], user["password"])

    # Cari semua GPS location IDs
    gps_location_ids = location_model.search([], limit=None)

    if not gps_location_ids:
        return {"message": "No GPS locations to delete."}

    # Hapus semua GPS locations
    deleted = location_model.unlink(gps_location_ids)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete GPS locations")

    return {
        "message": f"Successfully deleted {len(gps_location_ids)} GPS locations from all fleets"
    }