from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import get_db_connection, init_database
from models import (
    UserCreate, UserLogin, TOTPVerify, TokenResponse,
    TOTPSetup, CameraCreate, CameraGeoJSON
)
from utils.auth import (
    hash_password, verify_password, create_access_token,
    generate_totp_secret, verify_totp, generate_qr_code, verify_token
)
from services.camera_service import (
    sync_cameras_from_sheets, get_cameras_geojson, import_cameras_from_file
)
from datetime import datetime, timedelta
import secrets
import pandas as pd
import io
from typing import Optional

app = FastAPI(title="Camera GIS API")

# CORS middleware - restrict to trusted origins only
import os
allowed_origins = [
    "http://localhost:5000",
    "https://localhost:5000",
]
if os.getenv("REPLIT_DOMAINS"):
    domains = os.getenv("REPLIT_DOMAINS").split(",")
    for domain in domains:
        allowed_origins.append(f"https://{domain.strip()}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()

# Authentication dependency
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.user_id, s.is_2fa_validated, s.expires_at, u.username
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ?
        """, (token,))
        session = cursor.fetchone()

        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")

        if datetime.fromisoformat(session['expires_at']) < datetime.now():
            raise HTTPException(status_code=401, detail="Session expired")

        if not session['is_2fa_validated']:
            raise HTTPException(status_code=401, detail="2FA required")

        return {
            "user_id": session['user_id'],
            "username": session['username']
        }

# Auth endpoints
@app.post("/api/auth/register", response_model=TOTPSetup)
async def register(user: UserCreate):
    """Register new user and setup 2FA"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                      (user.username, user.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")

        # Create user
        totp_secret = generate_totp_secret()
        password_hash = hash_password(user.password)

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, totp_secret)
            VALUES (?, ?, ?, ?)
        """, (user.username, user.email, password_hash, totp_secret))
        conn.commit()

        # Generate QR code
        qr_code_url = generate_qr_code(totp_secret, user.username)

        return TOTPSetup(
            secret=totp_secret,
            qr_code_url=qr_code_url,
            manual_entry_key=totp_secret
        )

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and create session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, password_hash, totp_secret 
            FROM users 
            WHERE username = ? AND is_active = 1
        """, (credentials.username,))
        user = cursor.fetchone()

        if not user or not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create session
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=24)

        cursor.execute("""
            INSERT INTO sessions (session_token, user_id, expires_at, is_2fa_validated)
            VALUES (?, ?, ?, ?)
        """, (session_token, user['id'], expires_at, False))
        conn.commit()

        return TokenResponse(
            access_token=session_token,
            requires_2fa=True
        )

@app.post("/api/auth/verify-2fa")
async def verify_2fa(verify: TOTPVerify, authorization: Optional[str] = Header(None)):
    """Verify TOTP code and activate session"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.user_id, u.totp_secret
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ?
        """, (token,))
        session = cursor.fetchone()

        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")

        if not verify_totp(session['totp_secret'], verify.totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

        cursor.execute("""
            UPDATE sessions SET is_2fa_validated = 1
            WHERE session_token = ?
        """, (token,))
        conn.commit()

        return {"status": "success", "message": "2FA verified"}

@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate session"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"status": "success", "message": "Logged out successfully"}

# Camera endpoints
@app.get("/api/v1/cameras")
async def get_cameras(
    bbox: Optional[str] = None,
    status: Optional[str] = None,
    camera_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get cameras with filtering"""
    return get_cameras_geojson(bbox=bbox, status=status, camera_type=camera_type)

@app.post("/api/data/sync-sheets")
async def sync_sheets(
    spreadsheet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Sync cameras from Google Sheets"""
    result = sync_cameras_from_sheets(spreadsheet_id)
    return result

@app.post("/api/data/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload CSV or XLSX file with camera data"""
    try:
        contents = await file.read()

        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Convert DataFrame to list of dicts
        data = df.to_dict('records')
        result = import_cameras_from_file(data)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)