from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import logging
from datetime import datetime
import os
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Embedder Service",
    version="1.0.0",
    description="YandexGPT embedding wrapper with batching and retry"
)

# Configuration
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_EMBED_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"
MODEL_URI = f"emb://{YANDEX_FOLDER_ID}/text-search-doc/latest"

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Models
class EmbedRequest(BaseModel):
    text: str = Field(..., max_length=8000, description="Text to embed")
    chunk_id: Optional[str] = None

class EmbedResponse(BaseModel):
    embedding: List[float]
    chunk_id: Optional[str] = None
    model: str

class BatchEmbedRequest(BaseModel):
    texts: List[str] = Field(..., max_items=10, description="Batch of texts")
    metadata: Optional[dict] = None

class BatchEmbedResponse(BaseModel):
    embeddings: List[List[float]]
    count: int
    metadata: Optional[dict] = None

# Helper functions
async def generate_embedding(text: str, retry_count: int = 0) -> List[float]:
    """Generate embedding with retry logic"""
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "modelUri": MODEL_URI,
        "text": text[:8000]  # YandexGPT limit
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                YANDEX_EMBED_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data["embedding"]
    
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"Embedding failed (attempt {retry_count + 1}), retrying...")
            await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
            return await generate_embedding(text, retry_count + 1)
        else:
            logger.error(f"Embedding failed after {MAX_RETRIES} retries: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

# Endpoints
@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """
    Generate embedding for single text
    Includes automatic retry logic
    """
    logger.info(f"Generating embedding (length: {len(request.text)} chars)")
    
    embedding = await generate_embedding(request.text)
    
    return EmbedResponse(
        embedding=embedding,
        chunk_id=request.chunk_id,
        model=MODEL_URI
    )

@app.post("/embed/batch", response_model=BatchEmbedResponse)
async def embed_batch(request: BatchEmbedRequest):
    """
    Generate embeddings for batch of texts
    Processes in parallel with error handling
    """
    logger.info(f"Generating embeddings for batch of {len(request.texts)} texts")
    
    # Generate embeddings in parallel
    tasks = [generate_embedding(text) for text in request.texts]
    embeddings = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out errors
    valid_embeddings = [
        emb for emb in embeddings 
        if not isinstance(emb, Exception)
    ]
    
    if len(valid_embeddings) == 0:
        raise HTTPException(status_code=500, detail="All embeddings failed")
    
    if len(valid_embeddings) < len(request.texts):
        logger.warning(f"Some embeddings failed: {len(valid_embeddings)}/{len(request.texts)} succeeded")
    
    return BatchEmbedResponse(
        embeddings=valid_embeddings,
        count=len(valid_embeddings),
        metadata=request.metadata
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "embedder-service",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/test-connection")
async def test_yandex_connection():
    """Test YandexGPT API connection"""
    try:
        test_text = "Hello, world!"
        embedding = await generate_embedding(test_text)
        return {
            "status": "connected",
            "embedding_length": len(embedding),
            "model": MODEL_URI
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
