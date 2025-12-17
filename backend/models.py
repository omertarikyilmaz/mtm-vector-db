from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class DocumentBase(BaseModel):
    """Base model for document data"""
    title: str = Field(..., min_length=1, max_length=500, description="Doküman başlığı")
    content: str = Field(..., min_length=1, description="Doküman içeriği")
    source: Optional[str] = Field(None, description="Kaynak (URL, dosya adı, vb.)")
    source_type: Optional[str] = Field(None, description="Kaynak tipi (haber, makale, rapor, vb.)")
    category: Optional[str] = Field(None, description="Kategori")
    tags: Optional[List[str]] = Field(default_factory=list, description="Etiketler")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Ek metadata")


class DocumentCreate(DocumentBase):
    """Model for creating a new document"""
    pass


class DocumentUpdate(BaseModel):
    """Model for updating a document"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    source: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Document(DocumentBase):
    """Full document model with ID and timestamps"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BulkDocumentCreate(BaseModel):
    """Model for bulk document creation"""
    documents: List[DocumentCreate]


class SearchQuery(BaseModel):
    """Model for search queries"""
    query: str = Field(..., min_length=1, description="Arama sorgusu")
    limit: int = Field(default=10, ge=1, le=100, description="Maksimum sonuç sayısı")
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum benzerlik skoru")
    filter_category: Optional[str] = Field(None, description="Kategori filtresi")
    filter_source_type: Optional[str] = Field(None, description="Kaynak tipi filtresi")
    filter_tags: Optional[List[str]] = Field(None, description="Etiket filtresi")


class SimilarQuery(BaseModel):
    """Model for finding similar documents"""
    document_id: str = Field(..., description="Referans doküman ID")
    limit: int = Field(default=10, ge=1, le=100, description="Maksimum sonuç sayısı")
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Model for search results"""
    id: str
    title: str
    content: str
    source: Optional[str]
    source_type: Optional[str]
    category: Optional[str]
    tags: List[str]
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Model for search response"""
    query: str
    total_results: int
    results: List[SearchResult]
    relationships: Optional[List[Dict[str, Any]]] = None


class RelationshipNode(BaseModel):
    """Model for relationship graph nodes"""
    id: str
    title: str
    category: Optional[str]
    source_type: Optional[str]


class RelationshipEdge(BaseModel):
    """Model for relationship graph edges"""
    source: str
    target: str
    weight: float  # similarity score


class RelationshipGraph(BaseModel):
    """Model for relationship visualization"""
    nodes: List[RelationshipNode]
    edges: List[RelationshipEdge]


class CollectionStats(BaseModel):
    """Model for collection statistics"""
    total_documents: int
    categories: Dict[str, int]
    source_types: Dict[str, int]
    tags: Dict[str, int]
