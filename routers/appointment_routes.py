from fastapi import APIRouter, Depends, HTTPException
from typing import List
from schemas.appointment_schema import AppointmentCreate, AppointmentOut, AppointmentUpdate, AppointmentOut2, AppointmentStateUpdate
from odoo_client.base_model import OdooModel
from dependencies.auth_dep import get_odoo_user
from helper.helper import preprocess_odoo_data, normalize_relations

router = APIRouter(prefix="/appointments", tags=["Appointments"])

# @router.get("/", response_model=List[AppointmentOut])
# def get_appointments(user=Depends(get_odoo_user)):
#     appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])
#     appointments = appointment_model.search_read(fields=[
#         'id', 'reference', 'patient_id', 'date_appointment', 'note', 'state',
#         'appointment_line_ids', 'display_name', 'total_qty', 'date_of_birth'
#     ], limit=50)
#     # appointments = preprocess_odoo_data(data_dict) # process data
#     clean_appointments = [normalize_relations(appointment) for appointment in appointments]
#     print(clean_appointments)
#     return clean_appointments
    
@router.get("/", response_model=List[AppointmentOut])
def get_appointments(user=Depends(get_odoo_user)):
    try:
        appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])
        appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])

        # Step 1: Ambil semua appointment
        appointments = appointment_model.search_read(fields=[
            'id', 'reference', 'patient_id', 'date_appointment', 'note', 'state',
            'appointment_line_ids', 'display_name', 'total_qty', 'date_of_birth'
        ], limit=100)

        if not appointments:
            return []

        # Step 2: Kumpulkan semua ID line dari semua appointment
        all_line_ids = []
        for appt in appointments:
            all_line_ids.extend(appt.get("appointment_line_ids", []))

        # Step 3: Baca semua line sekalian
        line_map = {}
        if all_line_ids:
            line_details = appointment_line_model.read(all_line_ids, fields=["id", "appointment_id", "product_id", "qty"])
            for line in line_details:
                if line.get("appointment_id"):
                    appt_id = line["appointment_id"][0]
                    if appt_id not in line_map:
                        line_map[appt_id] = []
                    line_map[appt_id].append({
                        "id": line["id"],
                        "product_id": line["product_id"][0] if isinstance(line["product_id"], list) else line["product_id"],
                        "qty": line["qty"]
                    })
        print("line_map:", line_map)

        # Step 4: Gabungkan appointment dengan line-nya
        result = []
        for appt in appointments:
            result.append({
                "id": appt["id"],
                "reference": appt["reference"],
                "patient_id": appt["patient_id"][0] if isinstance(appt["patient_id"], list) else None,
                "date_appointment": appt.get("date_appointment"),
                "note": appt.get("note"),
                "state": appt["state"],
                "appointment_line_ids": line_map.get(appt["id"], []),
                "display_name": appt.get("display_name"),
                "total_qty": appt.get("total_qty"),
                "date_of_birth": appt.get("date_of_birth")
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, user=Depends(get_odoo_user)):
    appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])

    # # Read appointment data from Odoo
    # appointment = appointment_model.read([appointment_id], fields=[
    #     'id', 'reference', 'patient_id', 'date_appointment', 'note', 'state',
    #     'appointment_line_ids', 'display_name', 'total_qty', 'date_of_birth'
    # ])
    # if not appointment:
    #     raise HTTPException(status_code=404, detail="Appointment not found")
    # clean_appointment = normalize_relations(appointment[0])

    # return clean_appointment
    # Read hasil appointment
    appointment_data = appointment_model.read([appointment_id], fields=[
        'id', 'reference', 'patient_id', 'date_appointment', 'note', 'state', 
        'display_name', 'total_qty', 'date_of_birth', 'appointment_line_ids'
    ])[0]

    # Baca detail appointment_line jika perlu (optional)
    line_ids = appointment_data.get("appointment_line_ids", [])
    appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])
    line_details = appointment_line_model.read(line_ids, fields=["id", "product_id", "qty"])

    # Format hasil line
    formatted_lines = [
        {
            "id": line["id"],
            "product_id": line["product_id"][0],
            "qty": line["qty"]
        }
        for line in line_details
    ]

    return {
        "id": appointment_data['id'],
        "reference": appointment_data['reference'],
        "patient_id": appointment_data['patient_id'][0],
        "date_appointment": appointment_data.get('date_appointment'),
        "note": appointment_data.get('note'),
        "state": appointment_data['state'],
        "appointment_line_ids": formatted_lines,  # kalau mau detail line, ambil lagi pakai read()
        "display_name": appointment_data.get('display_name'),
        "total_qty": appointment_data.get('total_qty'),
        "date_of_birth": appointment_data.get('date_of_birth')
    }

@router.post("/", response_model=AppointmentOut)
def create_appointment(data: AppointmentCreate, user=Depends(get_odoo_user)):
    try:
        appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])

        # Ubah appointment_line_ids ke command tuple
        raw_data = data.dict()
        lines = raw_data.pop("appointment_line_ids", [])
        formatted_lines = [(0, 0, {"product_id": line["product_id"], "qty": line["qty"]}) for line in lines]

        # Gabungkan data
        data_dict = preprocess_odoo_data({**raw_data, "appointment_line_ids": formatted_lines})

        # Create appointment
        new_id = appointment_model.create(data_dict)

        # Read hasil appointment
        appointment_data = appointment_model.read([new_id], fields=[
            'id', 'reference', 'patient_id', 'date_appointment', 'note', 'state', 
            'display_name', 'total_qty', 'date_of_birth', 'appointment_line_ids'
        ])[0]

        # Baca detail appointment_line jika perlu (optional)
        line_ids = appointment_data.get("appointment_line_ids", [])
        appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])
        line_details = appointment_line_model.read(line_ids, fields=["product_id", "qty"])

        # Format hasil line
        formatted_lines = [
            {
                "id": line["id"],
                "product_id": line["product_id"][0],
                "qty": line["qty"]
            }
            for line in line_details
        ]

        return {
            "id": appointment_data['id'],
            "reference": appointment_data['reference'],
            "patient_id": appointment_data['patient_id'][0],
            "date_appointment": appointment_data.get('date_appointment'),
            "note": appointment_data.get('note'),
            "state": appointment_data['state'],
            "appointment_line_ids": formatted_lines,  # kalau mau detail line, ambil lagi pakai read()
            "display_name": appointment_data.get('display_name'),
            "total_qty": appointment_data.get('total_qty'),
            "date_of_birth": appointment_data.get('date_of_birth')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Post without line
@router.post("/createonly/", response_model=AppointmentOut)
def create_appointment(data: AppointmentCreate, user=Depends(get_odoo_user)):
    try:
        appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])
        data_dict = preprocess_odoo_data(data.dict())

        # Create appointment
        appointment_id = appointment_model.create(data_dict)
        appointment = appointment_model.read([appointment_id], fields=[
            'id', 'patient_id', 'date_appointment', 'note', 'state',
            'appointment_line_ids', 'display_name', 'total_qty', 'date_of_birth'
        ])
        clean_appointment = normalize_relations(appointment[0])
        return clean_appointment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, data: AppointmentUpdate, user=Depends(get_odoo_user)):
    try:
        appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])
        # Ubah appointment_line_ids ke command tuple
        raw_data = data.dict()
        lines = raw_data.pop("appointment_line_ids", [])
        formatted_lines = [(1, line["id"], {"product_id": line["product_id"], "qty": line["qty"]}) for line in lines]
        # Gabungkan data
        data_dict = preprocess_odoo_data({**raw_data, "appointment_line_ids": formatted_lines})
        # Update appointment in Odoo
        appointment_model.write([appointment_id], data_dict)

        # Read hasil appointment
        appointment_data = appointment_model.read([appointment_id], fields=[
            'id', 'reference', 'patient_id', 'date_appointment', 'note', 'state', 
            'display_name', 'total_qty', 'date_of_birth', 'appointment_line_ids'
        ])[0]
        # Baca detail appointment_line jika perlu (optional)
        line_ids = appointment_data.get("appointment_line_ids", [])
        appointment_line_model = OdooModel("hospital.appointment.line", user["uid"], user["username"], user["password"])
        line_details = appointment_line_model.read(line_ids, fields=["product_id", "qty"])
        # Format hasil line
        formatted_lines = [
            {
                "id": line["id"],
                "product_id": line["product_id"][0],
                "qty": line["qty"]
            }
            for line in line_details
        ]
        return {
            "id": appointment_data['id'],
            "reference": appointment_data['reference'],
            "patient_id": appointment_data['patient_id'][0],
            "date_appointment": appointment_data.get('date_appointment'),
            "note": appointment_data.get('note'),
            "state": appointment_data['state'],
            "appointment_line_ids": formatted_lines, 
            "display_name": appointment_data.get('display_name'),
            "total_qty": appointment_data.get('total_qty'),
            "date_of_birth": appointment_data.get('date_of_birth')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/updateonly/{appointment_id}", response_model=AppointmentOut2)
def update_appointment(appointment_id: int, data: AppointmentUpdate, user=Depends(get_odoo_user)):
    appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])

    # Preprocess data
    preprocessed_data = preprocess_odoo_data(data.dict(exclude_unset=True)) # process data

    # Update appointment in Odoo
    appointment_model.write([appointment_id], preprocessed_data)

    # Get updated appointment data from Odoo
    appointment = appointment_model.read([appointment_id], fields=[
        'id', 'reference', 'patient_id', 'date_appointment', 'note', 'state',
        'appointment_line_ids', 'display_name', 'total_qty', 'date_of_birth'
    ])

    # Normalize relations
    clean_appointment = normalize_relations(appointment[0])

    return clean_appointment
    
@router.put("/{appointment_id}/state")
def update_appointment_state(appointment_id: int, data: AppointmentStateUpdate, user=Depends(get_odoo_user)):
    appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])
    # Get updated appointment data from Odoo
    appointment = appointment_model.read([appointment_id], fields=['state'])
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    current_state = appointment[0]['state']
    new_state = data.state
    valid_transitions = {
        "draft": ["confirmed", "cancelled"],
        "confirmed": ["ongoing", "cancelled"],
        "ongoing": ["done", "cancelled"],
        "done": [],
        "cancelled": []
    }
    if new_state not in valid_transitions.get(current_state, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition from '{current_state}' to '{new_state}'"
        )
    appointment_model.write([appointment_id], {"state": new_state})
    updated_appointment = appointment_model.read([appointment_id], fields=["state"])

    return {
        "appointment_id": appointment_id,
        "old_state": current_state,
        "new_state": updated_appointment[0]["state"]
    }
    


@router.delete("/{appointment_id}", status_code=204)
def delete_appointment(appointment_id: int, user=Depends(get_odoo_user)):
    appointment_model = OdooModel("hospital.appointment", user["uid"], user["username"], user["password"])

    # Delete the appointment
    result = appointment_model.unlink([appointment_id])

    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"message": "Appointment deleted successfully"}
