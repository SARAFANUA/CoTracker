from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TOTPVerify(BaseModel):
    totp_code: str

class CameraBase(BaseModel):
    name: str
    status: str
    camera_type: str
    description: Optional[str] = None
    direction: Optional[float] = None
    field_of_view: Optional[float] = None
    latitude: float
    longitude: float

class CameraCreate(CameraBase):
    g_sheet_row_id: Optional[str] = None

class CameraResponse(CameraBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CameraGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: list

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False

class TOTPSetup(BaseModel):
    secret: str
    qr_code_url: str
    manual_entry_key: str
