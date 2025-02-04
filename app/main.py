from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models
from app.database import engine, get_db
from app.routers import public, private
from app.dependencies import get_current_active_admin

# Models should be created via Alembic migrations in production
# Remove this in production after setting up migrations
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Group Maker API",
    description="API for creating and managing groups with preferences and restrictions",
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

# Improved CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
    ],  # Update with your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with proper dependencies
app.include_router(
    public.router,
    prefix="/api/v1",
    tags=["Public"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    private.router,
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_active_admin)]
)

# Enhanced health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Service Health Check",
    response_description="Returns service health status"
)
async def health_check(db: Session = Depends(get_db)):
    """
    Perform a comprehensive health check of the service including database connectivity.
    """
    # Simple database connectivity check
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}