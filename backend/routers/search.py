from fastapi import APIRouter, HTTPException, status
from typing import List, Optional

from models import SearchQuery, SimilarQuery, SearchResponse, RelationshipGraph
from services.qdrant_service import get_qdrant_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_documents(query: SearchQuery):
    """Search for documents using semantic similarity"""
    service = get_qdrant_service()
    
    results = service.search(
        query=query.query,
        limit=query.limit,
        score_threshold=query.score_threshold,
        filter_category=query.filter_category,
        filter_source_type=query.filter_source_type,
        filter_tags=query.filter_tags
    )
    
    # Get relationships for found documents
    relationships = None
    if len(results) >= 2:
        doc_ids = [r["id"] for r in results]
        nodes, edges = service.get_relationships(doc_ids, similarity_threshold=0.5)
        relationships = {"nodes": nodes, "edges": edges}
    
    return SearchResponse(
        query=query.query,
        total_results=len(results),
        results=[
            {
                "id": r["id"],
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "source": r.get("source"),
                "source_type": r.get("source_type"),
                "category": r.get("category"),
                "tags": r.get("tags", []),
                "score": r.get("score", 0),
                "metadata": r.get("metadata", {})
            }
            for r in results
        ],
        relationships=relationships
    )


@router.post("/similar", response_model=dict)
async def find_similar(query: SimilarQuery):
    """Find documents similar to a given document"""
    service = get_qdrant_service()
    
    # Check if document exists
    doc = service.get_document(query.document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referans doküman bulunamadı"
        )
    
    results = service.find_similar(
        doc_id=query.document_id,
        limit=query.limit,
        score_threshold=query.score_threshold
    )
    
    return {
        "reference_document": {
            "id": doc["id"],
            "title": doc.get("title", "")
        },
        "similar_documents": results,
        "total_found": len(results)
    }


@router.get("/explore", response_model=RelationshipGraph)
async def explore_relationships(
    limit: int = 50,
    category: Optional[str] = None,
    source_type: Optional[str] = None
):
    """Get relationship graph for exploration"""
    service = get_qdrant_service()
    
    # Get all documents with optional filters
    all_docs = service.get_all_documents(limit=limit)
    
    if category:
        all_docs = [d for d in all_docs if d.get("category") == category]
    if source_type:
        all_docs = [d for d in all_docs if d.get("source_type") == source_type]
    
    if len(all_docs) < 2:
        return RelationshipGraph(nodes=[], edges=[])
    
    doc_ids = [d["id"] for d in all_docs]
    nodes, edges = service.get_relationships(doc_ids, similarity_threshold=0.5)
    
    return RelationshipGraph(nodes=nodes, edges=edges)
