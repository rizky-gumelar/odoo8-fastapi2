from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from config.settings import settings

bearer_scheme = HTTPBearer()

def get_odoo_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    try:
        payload = jwt.decode(token.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return {
            "uid": payload["uid"],
            "username": payload["username"],
            "password": payload["password"]
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
