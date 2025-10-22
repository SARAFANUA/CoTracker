import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import get_db_connection
from services.google_sheets import read_sheet_data, validate_coordinates
from typing import List, Dict, Any, Optional
import json

def sync_cameras_from_sheets(spreadsheet_id: str) -> Dict[str, Any]:
    """Sync camera data from Google Sheets to database"""
    sheet_data = read_sheet_data(spreadsheet_id)
    
    if not sheet_data:
        return {"status": "error", "message": "No data retrieved from Google Sheets"}
    
    added = 0
    updated = 0
    errors = 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for row in sheet_data:
            try:
                lat, lon = validate_coordinates(
                    row.get('latitude', ''),
                    row.get('longitude', '')
                )
                
                if lat is None or lon is None:
                    errors += 1
                    continue
                
                name = row.get('name', 'Unnamed Camera')
                status = row.get('status', 'Active')
                camera_type = row.get('type', 'Fixed')
                description = row.get('description', '')
                direction = float(row.get('direction', 0) or 0)
                fov = float(row.get('field_of_view', 90) or 90)
                g_sheet_row_id = row.get('g_sheet_row_id')
                
                # Check if camera exists
                cursor.execute(
                    "SELECT id FROM cameras WHERE g_sheet_row_id = ?",
                    (g_sheet_row_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing camera
                    cursor.execute("""
                        UPDATE cameras 
                        SET name = ?, status = ?, camera_type = ?, description = ?,
                            direction = ?, field_of_view = ?, 
                            geometry = GeomFromText(?, 4326),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE g_sheet_row_id = ?
                    """, (name, status, camera_type, description, direction, fov,
                          f'POINT({lon} {lat})', g_sheet_row_id))
                    updated += 1
                else:
                    # Insert new camera
                    cursor.execute("""
                        INSERT INTO cameras 
                        (g_sheet_row_id, name, status, camera_type, description, 
                         direction, field_of_view, geometry)
                        VALUES (?, ?, ?, ?, ?, ?, ?, GeomFromText(?, 4326))
                    """, (g_sheet_row_id, name, status, camera_type, description,
                          direction, fov, f'POINT({lon} {lat})'))
                    added += 1
                
            except Exception as e:
                print(f"Error processing row: {e}")
                errors += 1
        
        conn.commit()
    
    return {
        "status": "success",
        "added": added,
        "updated": updated,
        "errors": errors
    }

def get_cameras_geojson(
    bbox: Optional[str] = None,
    status: Optional[str] = None,
    camera_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get cameras as GeoJSON with filtering"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT id, g_sheet_row_id, name, status, camera_type, description,
                   direction, field_of_view, created_at, updated_at,
                   ST_X(geometry) as longitude, ST_Y(geometry) as latitude
            FROM cameras
            WHERE 1=1
        """
        params = []
        
        # Apply bounding box filter
        if bbox:
            try:
                bbox_parts = [float(x) for x in bbox.split(',')]
                if len(bbox_parts) == 4:
                    min_lon, min_lat, max_lon, max_lat = bbox_parts
                    query += """
                        AND ST_Intersects(
                            geometry, 
                            BuildMbr(?, ?, ?, ?, 4326)
                        )
                    """
                    params.extend([min_lon, min_lat, max_lon, max_lat])
            except:
                pass
        
        # Apply status filter
        if status:
            query += " AND status = ?"
            params.append(status)
        
        # Apply type filter
        if camera_type:
            query += " AND camera_type = ?"
            params.append(camera_type)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        features = []
        for row in rows:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['longitude'], row['latitude']]
                },
                "properties": {
                    "id": row['id'],
                    "name": row['name'],
                    "status": row['status'],
                    "camera_type": row['camera_type'],
                    "description": row['description'],
                    "direction": row['direction'],
                    "field_of_view": row['field_of_view']
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }

def import_cameras_from_file(file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Import cameras from uploaded CSV/XLSX file"""
    added = 0
    errors = 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for row in file_data:
            try:
                lat, lon = validate_coordinates(
                    row.get('latitude', ''),
                    row.get('longitude', '')
                )
                
                if lat is None or lon is None:
                    errors += 1
                    continue
                
                cursor.execute("""
                    INSERT INTO cameras 
                    (name, status, camera_type, description, direction, field_of_view, geometry)
                    VALUES (?, ?, ?, ?, ?, ?, GeomFromText(?, 4326))
                """, (
                    row.get('name', 'Unnamed Camera'),
                    row.get('status', 'Active'),
                    row.get('type', 'Fixed'),
                    row.get('description', ''),
                    float(row.get('direction', 0) or 0),
                    float(row.get('field_of_view', 90) or 90),
                    f'POINT({lon} {lat})'
                ))
                added += 1
                
            except Exception as e:
                print(f"Error importing row: {e}")
                errors += 1
        
        conn.commit()
    
    return {"status": "success", "added": added, "errors": errors}
