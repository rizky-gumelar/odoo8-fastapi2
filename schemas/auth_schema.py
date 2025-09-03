from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str = "admin"
    password: str = "1234"

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
