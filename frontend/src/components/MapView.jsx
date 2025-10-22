import React, { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { Deck } from '@deck.gl/core'
import { ScatterplotLayer } from '@deck.gl/layers'
import 'maplibre-gl/dist/maplibre-gl.css'

const STATUS_COLORS = {
  'Active': [76, 175, 80, 200],
  'Inactive': [244, 67, 54, 200],
  'Maintenance': [255, 152, 0, 200]
}

function MapView({ token, onLogout }) {
  const mapContainer = useRef(null)
  const mapRef = useRef(null)
  const deckRef = useRef(null)
  
  const [cameras, setCameras] = useState([])
  const [filters, setFilters] = useState({
    status: '',
    camera_type: ''
  })
  const [spreadsheetId, setSpreadsheetId] = useState('')
  const [uploadMessage, setUploadMessage] = useState('')

  useEffect(() => {
    if (!mapContainer.current) return

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [30, 50],
      zoom: 5
    })

    mapRef.current = map

    map.on('load', () => {
      loadCameras()
      
      map.on('moveend', () => {
        loadCameras()
      })
    })

    return () => {
      if (deckRef.current) {
        deckRef.current.finalize()
      }
      map.remove()
    }
  }, [])

  useEffect(() => {
    if (mapRef.current && mapRef.current.loaded()) {
      loadCameras()
    }
  }, [filters])

  useEffect(() => {
    updateDeckLayer()
  }, [cameras])

  const loadCameras = async () => {
    if (!mapRef.current) return

    const bounds = mapRef.current.getBounds()
    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`

    const params = new URLSearchParams({ bbox })
    if (filters.status) params.append('status', filters.status)
    if (filters.camera_type) params.append('camera_type', filters.camera_type)

    try {
      const response = await fetch(`/api/v1/cameras?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) throw new Error('Failed to fetch cameras')

      const data = await response.json()
      const cameraPoints = data.features.map(feature => ({
        position: feature.geometry.coordinates,
        properties: feature.properties
      }))
      
      setCameras(cameraPoints)
    } catch (err) {
      console.error('Error loading cameras:', err)
    }
  }

  const updateDeckLayer = () => {
    if (!mapRef.current) return

    if (deckRef.current) {
      deckRef.current.finalize()
    }

    const deck = new Deck({
      canvas: 'deck-canvas',
      width: '100%',
      height: '100%',
      initialViewState: {
        longitude: mapRef.current.getCenter().lng,
        latitude: mapRef.current.getCenter().lat,
        zoom: mapRef.current.getZoom(),
        pitch: 0,
        bearing: 0
      },
      controller: true,
      layers: [
        new ScatterplotLayer({
          id: 'cameras',
          data: cameras,
          getPosition: d => d.position,
          getFillColor: d => STATUS_COLORS[d.properties.status] || [128, 128, 128, 200],
          getRadius: 100,
          radiusMinPixels: 5,
          radiusMaxPixels: 15,
          pickable: true,
          onClick: info => {
            if (info.object) {
              const props = info.object.properties
              alert(`${props.name}\nType: ${props.camera_type}\nStatus: ${props.status}\n${props.description || ''}`)
            }
          }
        })
      ],
      onViewStateChange: ({ viewState }) => {
        mapRef.current.jumpTo({
          center: [viewState.longitude, viewState.latitude],
          zoom: viewState.zoom,
          bearing: viewState.bearing,
          pitch: viewState.pitch
        })
      }
    })

    deckRef.current = deck

    mapRef.current.on('move', () => {
      if (deckRef.current) {
        deckRef.current.setProps({
          viewState: {
            longitude: mapRef.current.getCenter().lng,
            latitude: mapRef.current.getCenter().lat,
            zoom: mapRef.current.getZoom(),
            pitch: mapRef.current.getPitch(),
            bearing: mapRef.current.getBearing()
          }
        })
      }
    })
  }

  const handleSyncSheets = async () => {
    if (!spreadsheetId) return

    setUploadMessage('Syncing...')
    try {
      const response = await fetch(`/api/data/sync-sheets?spreadsheet_id=${spreadsheetId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      const data = await response.json()
      setUploadMessage(`Synced! Added: ${data.added}, Updated: ${data.updated}, Errors: ${data.errors}`)
      loadCameras()
      
      setTimeout(() => setUploadMessage(''), 5000)
    } catch (err) {
      setUploadMessage('Error syncing data')
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    setUploadMessage('Uploading...')
    try {
      const response = await fetch('/api/data/upload-file', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      const data = await response.json()
      setUploadMessage(`Uploaded! Added: ${data.added}, Errors: ${data.errors}`)
      loadCameras()
      
      setTimeout(() => setUploadMessage(''), 5000)
    } catch (err) {
      setUploadMessage('Error uploading file')
    }
  }

  return (
    <div className="map-container">
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />
      <canvas id="deck-canvas" style={{ position: 'absolute', left: 0, top: 0, pointerEvents: 'all' }} />
      
      <div className="controls-panel">
        <h3 style={{ marginBottom: '15px' }}>Camera Controls</h3>
        
        <div className="control-group">
          <label>Status Filter</label>
          <select 
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">All Statuses</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
            <option value="Maintenance">Maintenance</option>
          </select>
        </div>

        <div className="control-group">
          <label>Camera Type Filter</label>
          <select
            value={filters.camera_type}
            onChange={(e) => setFilters({ ...filters, camera_type: e.target.value })}
          >
            <option value="">All Types</option>
            <option value="Fixed">Fixed</option>
            <option value="PTZ">PTZ</option>
            <option value="Dome">Dome</option>
          </select>
        </div>

        <div className="control-group">
          <label>Google Sheets ID</label>
          <input
            type="text"
            value={spreadsheetId}
            onChange={(e) => setSpreadsheetId(e.target.value)}
            placeholder="Enter spreadsheet ID"
          />
          <button onClick={handleSyncSheets}>Sync from Sheets</button>
        </div>

        <div className="control-group">
          <label>Upload CSV/XLSX</label>
          <input type="file" accept=".csv,.xlsx" onChange={handleFileUpload} />
        </div>

        {uploadMessage && (
          <div style={{ fontSize: '12px', color: '#4CAF50', marginTop: '10px' }}>
            {uploadMessage}
          </div>
        )}

        <button onClick={onLogout} style={{ marginTop: '10px', background: '#f44336' }}>
          Logout
        </button>
      </div>
    </div>
  )
}

export default MapView
