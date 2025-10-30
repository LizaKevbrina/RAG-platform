from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Validation Service",
    version="1.0.0",
    description="File validation for RAG pipeline"
)

# Models
class FileValidationRequest(BaseModel):
    file_id: str = Field(..., description="Google Drive file ID")
    file_name: str = Field(..., description="File name")
    file_type: str = Field(..., description="MIME type")
    file_size_bytes: int = Field(..., description="File size in bytes")

class FileValidationResponse(BaseModel):
    status: str  # VALID, INVALID
    file_id: str
    estimated_pages: Optional[int] = None
    error_message: Optional[str] = None
    validated_at: str

# Configuration
ALLOWED_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.google-apps.document',
    'application/vnd.google-apps.spreadsheet',
]

MAX_FILE_SIZE_MB = 50

# Endpoints
@app.post("/validate", response_model=FileValidationResponse)
async def validate_file(request: FileValidationRequest):
    """
    Validate file for RAG processing
    
    Checks:
    - File type is supported
    - File size is within limits
    - Estimates processing pages
    """
    logger.info(f"Validating file: {request.file_id} ({request.file_name})")
    
    # Check file type
    if request.file_type not in ALLOWED_TYPES:
        logger.warning(f"Unsupported file type: {request.file_type}")
        return FileValidationResponse(
            status="INVALID",
            file_id=request.file_id,
            error_message=f"Unsupported file type: {request.file_type}",
            validated_at=datetime.utcnow().isoformat()
        )
    
    # Check file size
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if request.file_size_bytes > max_size_bytes:
        size_mb = request.file_size_bytes / 1024 / 1024
        logger.warning(f"File too large: {size_mb:.2f}MB")
        return FileValidationResponse(
            status="INVALID",
            file_id=request.file_id,
            error_message=f"File too large: {size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)",
            validated_at=datetime.utcnow().isoformat()
        )
    
    # Estimate pages (rough calculation: 50KB per page)
    estimated_pages = max(1, request.file_size_bytes // (50 * 1024))
    
    logger.info(f"File validated: {request.file_id}, estimated pages: {estimated_pages}")
    
    return FileValidationResponse(
        status="VALID",
        file_id=request.file_id,
        estimated_pages=estimated_pages,
        validated_at=datetime.utcnow().isoformat()
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "validation-service",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    # TODO: Add Prometheus metrics
    return {
        "service": "validation-service",
        "uptime_seconds": 0,  # Implement uptime tracking
        "requests_total": 0    # Implement request counter
    }
