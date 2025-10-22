# Camera GIS System

## Overview

Camera GIS System is a web-based geospatial application for managing and visualizing camera installations on an interactive map. The system provides camera location tracking, status monitoring, and synchronization with Google Sheets for data management. Users can view camera positions, orientations, and fields of view on a map interface, with support for importing camera data from external sources.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Technology Stack**: React 19 with Vite as the build tool

The frontend uses a modern React-based single-page application architecture with these key design decisions:

1. **Map Visualization Framework**: Deck.gl integrated with MapLibre GL
   - **Problem**: Need to render camera locations, orientations, and fields of view on an interactive map
   - **Solution**: Deck.gl provides high-performance WebGL-based visualization layers on top of MapLibre GL base maps
   - **Rationale**: Deck.gl excels at rendering large datasets and complex geospatial overlays, while MapLibre GL offers an open-source alternative to Mapbox GL
   - **Pros**: High performance, extensive layer types, open-source
   - **Cons**: Steeper learning curve than simpler mapping libraries

2. **Build System**: Vite with hot module replacement
   - **Problem**: Fast development iteration and optimized production builds
   - **Solution**: Vite provides near-instantaneous hot reloading and efficient bundling
   - **Pros**: Extremely fast development experience, modern ESM-based architecture
   - **Cons**: Less mature ecosystem than webpack

3. **API Communication**: Proxy configuration to backend at port 8000
   - All `/api` requests are proxied to the FastAPI backend during development
   - This avoids CORS issues and simplifies the development workflow

### Backend Architecture

**Technology Stack**: FastAPI (Python) with SQLite/SpatiaLite for spatial data

1. **Web Framework**: FastAPI
   - **Problem**: Need high-performance API with automatic documentation and type safety
   - **Solution**: FastAPI leverages Python type hints for automatic validation and OpenAPI documentation
   - **Pros**: Excellent performance, automatic API docs, type safety, async support
   - **Cons**: Relatively newer framework compared to Flask/Django

2. **Authentication System**: Multi-layered security approach
   - **Password Hashing**: Passlib with bcrypt
   - **JWT Tokens**: Jose library for stateless authentication
   - **2FA Support**: TOTP-based two-factor authentication using PyOTP
   - **Rationale**: Defense-in-depth strategy combining password security, token-based auth, and optional 2FA
   - **Session Management**: Database-backed sessions table for tracking active user sessions

3. **Service Layer Pattern**: Separation of business logic from route handlers
   - `camera_service.py`: Handles camera data operations and synchronization
   - `google_sheets.py`: Manages Google Sheets API integration
   - `auth.py`: Centralized authentication utilities
   - **Rationale**: Improves testability, maintainability, and code organization

### Data Storage

**Primary Database**: SQLite with SpatiaLite extension

1. **Spatial Database Choice**: SpatiaLite (SQLite with spatial capabilities)
   - **Problem**: Need to store and query geospatial camera locations efficiently
   - **Solution**: SpatiaLite adds spatial data types and functions to SQLite
   - **Alternatives Considered**: PostGIS/PostgreSQL
   - **Rationale**: SpatiaLite provides sufficient spatial capabilities for this use case without requiring a separate database server
   - **Pros**: File-based, easy deployment, no server setup, adequate spatial support
   - **Cons**: Limited concurrent write performance, not ideal for high-traffic production

2. **Schema Design**:
   - **Users Table**: Stores user credentials, TOTP secrets, and account status
   - **Sessions Table**: Tracks active authentication sessions
   - **Cameras Table** (implied): Stores camera metadata including spatial coordinates, orientation, field of view, and sync identifiers

3. **Context Manager Pattern**: Database connections use Python context managers
   - **Rationale**: Ensures proper connection cleanup and prevents resource leaks
   - Automatic transaction management and connection pooling

### Authentication & Authorization

1. **JWT-based Authentication**:
   - Stateless token authentication for API requests
   - Bearer token scheme in Authorization headers
   - Configurable token expiration (30 minutes default)

2. **Two-Factor Authentication (2FA)**:
   - TOTP implementation using PyOTP
   - QR code generation for authenticator app setup
   - Optional per-user basis (stored in user table)

3. **Security Measures**:
   - CORS middleware with restricted origins
   - Replit domain support for deployment environments
   - Password hashing using bcrypt
   - Credential validation using Pydantic models

## External Dependencies

### Third-Party Services

1. **Google Sheets API Integration**:
   - **Purpose**: Synchronize camera data from external Google Sheets spreadsheets
   - **Authentication**: OAuth2 flow using Replit environment variables
   - **Required Credentials**:
     - `GOOGLE_OAUTH_ACCESS_TOKEN`
     - `GOOGLE_OAUTH_REFRESH_TOKEN`
     - `GOOGLE_OAUTH_CLIENT_ID`
     - `GOOGLE_OAUTH_CLIENT_SECRET`
   - **Functionality**: Bi-directional sync of camera locations, statuses, and metadata

2. **MapLibre GL / Mapbox Services**:
   - **Purpose**: Base map rendering and tile services
   - **Integration**: Client-side JavaScript library
   - **Note**: May require API tokens depending on tile source configuration

### Key Python Libraries

- **FastAPI**: Async web framework for API development
- **Passlib**: Password hashing with bcrypt
- **Jose**: JWT token encoding/decoding
- **PyOTP**: TOTP two-factor authentication
- **Google API Client**: Google Sheets integration
- **SpatiaLite**: SQLite spatial extension (system library)

### Key JavaScript Libraries

- **React 19**: UI component framework
- **Deck.gl**: WebGL-powered geospatial visualization
- **MapLibre GL**: Open-source map rendering engine
- **Vite**: Frontend build tool and dev server

### File Upload Support

- **Pandas**: CSV/Excel file parsing for camera data import
- Supports bulk camera imports from spreadsheet files

### Environment Configuration

The application expects deployment on Replit with automatic environment variable injection for:
- Google OAuth credentials
- Domain configuration (`REPLIT_DOMAINS`)
- Dynamic CORS origin allowlist based on deployment environment