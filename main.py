from fastapi import FastAPI
from auth.login import router as auth_router
from routers.partner_routes import router as partner_router
from routers.patient_routes import router as patient_router
from routers.appointment_routes import router as appointment_router
from routers.appointment_line_routes import router as appointment_line_routes
import uvicorn

app = FastAPI(
    title="Odoo XML-RPC FastAPI",
    description="API FastAPI untuk CRUD res.partner di Odoo via XML-RPC dengan login dinamis dan JWT",
    version="2.0.0"
)

app.include_router(auth_router)
app.include_router(partner_router)
app.include_router(patient_router)
app.include_router(appointment_router)
app.include_router(appointment_line_routes)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)