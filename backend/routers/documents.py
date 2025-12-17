from fastapi import APIRouter, HTTPException, status
from typing import List

from models import (
    DocumentCreate, DocumentUpdate, Document, 
    BulkDocumentCreate
)
from services.qdrant_service import get_qdrant_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_document(document: DocumentCreate):
    """Create a new document"""
    service = get_qdrant_service()
    doc_dict = document.model_dump()
    doc_id = service.add_document(doc_dict)
    return {"id": doc_id, "message": "Doküman başarıyla oluşturuldu"}


@router.post("/bulk", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_documents_bulk(bulk: BulkDocumentCreate):
    """Create multiple documents in bulk"""
    service = get_qdrant_service()
    docs = [doc.model_dump() for doc in bulk.documents]
    doc_ids = service.add_documents_bulk(docs)
    return {
        "ids": doc_ids,
        "count": len(doc_ids),
        "message": f"{len(doc_ids)} doküman başarıyla oluşturuldu"
    }


@router.get("", response_model=List[dict])
async def list_documents(limit: int = 100, offset: int = 0):
    """List all documents with pagination"""
    service = get_qdrant_service()
    documents = service.get_all_documents(limit=limit, offset=offset)
    return documents


@router.get("/stats", response_model=dict)
async def get_stats():
    """Get collection statistics"""
    service = get_qdrant_service()
    stats = service.get_collection_stats()
    return stats


@router.get("/{doc_id}", response_model=dict)
async def get_document(doc_id: str):
    """Get a document by ID"""
    service = get_qdrant_service()
    document = service.get_document(doc_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doküman bulunamadı"
        )
    return document


@router.put("/{doc_id}", response_model=dict)
async def update_document(doc_id: str, updates: DocumentUpdate):
    """Update a document"""
    service = get_qdrant_service()
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Güncellenecek alan belirtilmedi"
        )
    
    success = service.update_document(doc_id, update_dict)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doküman bulunamadı"
        )
    
    return {"id": doc_id, "message": "Doküman başarıyla güncellendi"}


@router.delete("/{doc_id}", response_model=dict)
async def delete_document(doc_id: str):
    """Delete a document"""
    service = get_qdrant_service()
    success = service.delete_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doküman silinemedi"
        )
    return {"id": doc_id, "message": "Doküman başarıyla silindi"}
