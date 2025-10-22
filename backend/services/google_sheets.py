from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from typing import List, Dict, Any
import os

def get_google_sheets_service():
    """Get Google Sheets API service using Replit integration"""
    try:
        # Replit integration provides credentials automatically
        token = os.getenv('GOOGLE_OAUTH_ACCESS_TOKEN')
        refresh_token = os.getenv('GOOGLE_OAUTH_REFRESH_TOKEN')
        
        if not token:
            raise ValueError("Google Sheets integration not configured")
        
        creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
        )
        
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Sheets service: {e}")
        return None

def read_sheet_data(spreadsheet_id: str, range_name: str = "Sheet1!A:H") -> List[Dict[str, Any]]:
    """Read data from Google Sheets"""
    service = get_google_sheets_service()
    if not service:
        return []
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return []
        
        headers = values[0]
        data = []
        
        for idx, row in enumerate(values[1:], start=2):
            if len(row) < len(headers):
                row.extend([''] * (len(headers) - len(row)))
            
            camera_data = {}
            for i, header in enumerate(headers):
                camera_data[header.lower().replace(' ', '_')] = row[i] if i < len(row) else ''
            
            camera_data['g_sheet_row_id'] = f"{spreadsheet_id}_{idx}"
            data.append(camera_data)
        
        return data
    except Exception as e:
        print(f"Error reading Google Sheets: {e}")
        return []

def validate_coordinates(lat: str, lon: str) -> tuple:
    """Validate and convert coordinates"""
    try:
        latitude = float(lat)
        longitude = float(lon)
        
        if not (-90 <= latitude <= 90):
            raise ValueError("Invalid latitude")
        if not (-180 <= longitude <= 180):
            raise ValueError("Invalid longitude")
        
        return latitude, longitude
    except (ValueError, TypeError):
        return None, None
