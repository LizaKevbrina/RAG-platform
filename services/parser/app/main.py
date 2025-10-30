from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import httpx
import asyncio
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Parser Service",
    version="1.0.0",
    description="LlamaParse wrapper for document parsing"
)

# Configuration
LLAMAPARSE_API_KEY = os.getenv("LLAMAPARSE_API_KEY")
LLAMAPARSE_UPLOAD_URL = "https://api.cloud.llamaindex.ai/api/parsing/upload"
LLAMAPARSE_JOB_URL = "https://api.cloud.llamaindex.ai/api/parsing/job"
LLAMAPARSE_RESULT_URL = "https://api.cloud.llamaindex.ai/api/v1/parsing/job"

MAX_RETRIES = 20
RETRY_DELAY = 10  # seconds

# Models
class ParseRequest(BaseModel):
    file_id: str
    file_url: str  # Pre-signed URL from Google Drive/Storage
    file_name: str

class ParseResponse(BaseModel):
    status: str  # PROCESSING, SUCCESS, ERROR
    file_id: str
    job_id: Optional[str] = None
    error_message: Optional[str] = None

class ParseStatusRequest(BaseModel):
    job_id: str

class ParseStatusResponse(BaseModel):
    status: str  # PENDING, SUCCESS, ERROR
    job_id: str
    retry_count: int
    error_message: Optional[str] = None

class ParseResultRequest(BaseModel):
    job_id: str

class ParsedPage(BaseModel):
    page_number: int
    text: str

class ParseResultResponse(BaseModel):
    status: str
    job_id: str
    pages: List[ParsedPage]
    total_pages: int

# Helper functions
async def upload_to_llamaparse(file_url: str) -> str:
    """Upload file to LlamaParse and return job_id"""
    headers = {"Authorization": f"Bearer {LLAMAPARSE_API_KEY}"}
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Download file from URL
        file_response = await client.get(file_url)
        file_content = file_response.content
        
        # Upload to LlamaParse
        files = {"file": ("document", file_content)}
        response = await client.post(
            LLAMAPARSE_UPLOAD_URL,
            headers=headers,
            files=files
        )
        response.raise_for_status()
        
        data = response.json()
        return data["id"]

async def check_parse_status(job_id: str) -> Dict:
    """Check LlamaParse job status"""
    headers = {"Authorization": f"Bearer {LLAMAPARSE_API_KEY}"}
    url = f"{LLAMAPARSE_JOB_URL}/{job_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

async def get_parse_result(job_id: str) -> Dict:
    """Get parsed result from LlamaParse"""
    headers = {"Authorization": f"Bearer {LLAMAPARSE_API_KEY}"}
    url = f"{LLAMAPARSE_RESULT_URL}/{job_id}/result/json"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

# Endpoints
@app.post("/parse/upload", response_model=ParseResponse)
async def upload_document(request: ParseRequest):
    """
    Upload document to LlamaParse for parsing
    Returns job_id for status checking
    """
    logger.info(f"Uploading document: {request.file_id}")
    
    try:
        job_id = await upload_to_llamaparse(request.file_url)
        
        logger.info(f"Upload successful: job_id={job_id}")
        
        return ParseResponse(
            status="PROCESSING",
            file_id=request.file_id,
            job_id=job_id
        )
    
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return ParseResponse(
            status="ERROR",
            file_id=request.file_id,
            error_message=str(e)
        )

@app.post("/parse/status", response_model=ParseStatusResponse)
async def check_status(request: ParseStatusRequest):
    """Check parsing status"""
    logger.info(f"Checking status for job: {request.job_id}")
    
    try:
        status_data = await check_parse_status(request.job_id)
        
        return ParseStatusResponse(
            status=status_data["status"],
            job_id=request.job_id,
            retry_count=0,
            error_message=status_data.get("error")
        )
    
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return ParseStatusResponse(
            status="ERROR",
            job_id=request.job_id,
            retry_count=0,
            error_message=str(e)
        )

@app.post("/parse/result", response_model=ParseResultResponse)
async def get_result(request: ParseResultRequest):
    """Get parsing result"""
    logger.info(f"Getting result for job: {request.job_id}")
    
    try:
        result_data = await get_parse_result(request.job_id)
        
        pages = []
        for idx, page in enumerate(result_data.get("pages", [])):
            pages.append(ParsedPage(
                page_number=idx + 1,
                text=page.get("text", "")
            ))
        
        return ParseResultResponse(
            status="SUCCESS",
            job_id=request.job_id,
            pages=pages,
            total_pages=len(pages)
        )
    
    except Exception as e:
        logger.error(f"Get result failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "parser-service",
        "timestamp": datetime.utcnow().isoformat()
    }
