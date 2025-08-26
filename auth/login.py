from fastapi import APIRouter, HTTPException
from schemas.auth_schema import LoginRequest, LoginResponse
from odoo_client.client import odoo_login
from config.settings import settings
import jwt
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["Auth"])

def create_jwt_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=LoginResponse)
def login_user(payload: LoginRequest):
    try:
        uid = odoo_login(payload.username, payload.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Odoo credentials")

    token_data = {
        "uid": uid,
        "username": payload.username,
        "password": payload.password  # sementara menyimpan password di jwt
    }

    token = create_jwt_token(token_data)
    return {"access_token": token}
