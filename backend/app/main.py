from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import test_connection
from app.core.errors import register_error_handlers
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.oauth import router as oauth_router
from app.api.accounts import router as accounts_router
from app.api.transfers import router as transfers_router
from app.api.audit_logs import router as audit_logs_router

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="""
CloudShift API - Cloud File Migration Service

Transfer files seamlessly between OneDrive and Google Drive with:
* OAuth 2.0 integration for secure cloud access
* Real-time transfer progress tracking
* Conflict detection and resolution
* File filtering and scheduling
* Comprehensive audit logging

**Interactive Documentation:**
* Swagger UI: /docs
* ReDoc: /redoc
* OpenAPI JSON: /openapi.json
    """,
    contact={
        "name": "CloudShift Support",
        "email": "support@cloudshift.example.com",
    },
    license_info={
        "name": "MIT License",
    },
)

# Register error handlers
register_error_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(accounts_router)
app.include_router(transfers_router)
app.include_router(audit_logs_router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Test database connection
    if settings.DATABASE_URL:
        db_connected = await test_connection()
        if db_connected:
            print("✓ Database connection successful")
        else:
            print("✗ Database connection failed - app will start but DB operations will fail")
    else:
        print("⚠ DATABASE_URL not configured - skipping database connection test")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print(f"Shutting down {settings.APP_NAME}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
