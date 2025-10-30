from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import os
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Storage Service",
    version="1.0.0",
    description="Supabase wrapper for vector storage"
)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Models
class DocumentInsert(BaseModel):
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]

class BatchDocumentInsert(BaseModel):
    documents: List[DocumentInsert]

class DocumentResponse(BaseModel):
    id: int
    content: str
    metadata: Dict[str, Any]
    created_at: str

class DeleteByFileRequest(BaseModel):
    file_id: str

class SearchRequest(BaseModel):
    query_embedding: List[float]
    limit: int = Field(default=5, le=20)
    file_id: Optional[str] = None

class SearchResult(BaseModel):
    id: int
    content: str
    metadata: Dict[str, Any]
    similarity: float

# Endpoints
@app.post("/documents/insert")
async def insert_document(doc: DocumentInsert):
    """Insert single document with embedding"""
    logger.info(f"Inserting document (file_id: {doc.metadata.get('file_id')})")
    
    try:
        result = supabase.table("documents").insert({
            "content": doc.content,
            "embedding": doc.embedding,
            "metadata": doc.metadata
        }).execute()
        
        return {"status": "success", "id": result.data[0]["id"]}
    
    except Exception as e:
        logger.error(f"Insert failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/batch-insert")
async def batch_insert_documents(batch: BatchDocumentInsert):
    """Insert multiple documents in batch"""
    logger.info(f"Batch inserting {len(batch.documents)} documents")
    
    try:
        docs_data = [
            {
                "content": doc.content,
                "embedding": doc.embedding,
                "metadata": doc.metadata
            }
            for doc in batch.documents
        ]
        
        result = supabase.table("documents").insert(docs_data).execute()
        
        return {
            "status": "success",
            "inserted_count": len(result.data)
        }
    
    except Exception as e:
        logger.error(f"Batch insert failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/delete-by-file")
async def delete_by_file_id(request: DeleteByFileRequest):
    """Delete all documents for a file_id (for versioning)"""
    logger.info(f"Deleting documents for file_id: {request.file_id}")
    
    try:
        result = supabase.table("documents").delete().eq(
            "metadata->>file_id", request.file_id
        ).execute()
        
        return {
            "status": "success",
            "deleted_count": len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/search", response_model=List[SearchResult])
async def semantic_search(request: SearchRequest):
    """
    Semantic search using vector similarity
    Uses pgvector's <-> operator
    """
    logger.info(f"Searching (limit: {request.limit})")
    
    try:
        # Build query
        query = supabase.rpc(
            "match_documents",
            {
                "query_embedding": request.embedding,
                "match_count": request.limit
            }
        )
        
        # Filter by file_id if provided
        if request.file_id:
            query = query.eq("metadata->>file_id", request.file_id)
        
        result = query.execute()
        
        return [
            SearchResult(
                id=row["id"],
                content=row["content"],
                metadata=row["metadata"],
                similarity=row["similarity"]
            )
            for row in result.data
        ]
    
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "storage-service",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/test-connection")
async def test_supabase_connection():
    """Test Supabase connection"""
    try:
        result = supabase.table("documents").select("id").limit(1).execute()
        return {
            "status": "connected",
            "url": SUPABASE_URL
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
