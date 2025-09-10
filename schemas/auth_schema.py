from pydantic import BaseModel

# class LoginRequest(BaseModel):
#     username: str = "rizksyah0406@sibasurya.com"
#     password: str = "1"

class LoginRequest(BaseModel):
    username: str = "admin"
    password: str = "1"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
