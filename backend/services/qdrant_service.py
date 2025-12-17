from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Optional, Dict, Any, Tuple
import os
import logging
import uuid
from datetime import datetime

from services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for interacting with Qdrant vector database"""
    
    def __init__(self):
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = os.getenv("COLLECTION_NAME", "medya_takip")
        
        logger.info(f"Connecting to Qdrant at {self.host}:{self.port}")
        self.client = QdrantClient(host=self.host, port=self.port)
        
        self.embedding_service = get_embedding_service()
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            logger.info(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_service.get_dimension(),
                    distance=Distance.COSINE
                )
            )
            
            # Create payload indexes for filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="category",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="source_type",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="tags",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logger.info(f"Collection created with indexes")
        else:
            logger.info(f"Collection {self.collection_name} already exists")
    
    def add_document(self, document: Dict[str, Any]) -> str:
        """Add a single document to the collection"""
        doc_id = document.get("id", str(uuid.uuid4()))
        
        # Create text for embedding (title + content)
        text_for_embedding = f"{document['title']} {document['content']}"
        vector = self.embedding_service.encode_single(text_for_embedding)
        
        # Prepare payload
        payload = {
            "title": document["title"],
            "content": document["content"],
            "source": document.get("source"),
            "source_type": document.get("source_type"),
            "category": document.get("category"),
            "tags": document.get("tags", []),
            "metadata": document.get("metadata", {}),
            "created_at": document.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": document.get("updated_at")
        }
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )
        
        logger.info(f"Document added with ID: {doc_id}")
        return doc_id
    
    def add_documents_bulk(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Add multiple documents in bulk"""
        doc_ids = []
        points = []
        
        # Prepare texts for batch embedding
        texts = [f"{doc['title']} {doc['content']}" for doc in documents]
        vectors = self.embedding_service.encode_batch(texts)
        
        for doc, vector in zip(documents, vectors):
            doc_id = doc.get("id", str(uuid.uuid4()))
            doc_ids.append(doc_id)
            
            payload = {
                "title": doc["title"],
                "content": doc["content"],
                "source": doc.get("source"),
                "source_type": doc.get("source_type"),
                "category": doc.get("category"),
                "tags": doc.get("tags", []),
                "metadata": doc.get("metadata", {}),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": None
            }
            
            points.append(PointStruct(
                id=doc_id,
                vector=vector,
                payload=payload
            ))
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Bulk added {len(doc_ids)} documents")
        return doc_ids
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[doc_id],
                with_payload=True
            )
            
            if results:
                point = results[0]
                return {
                    "id": point.id,
                    **point.payload
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {e}")
            return None
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """Update a document's payload and re-embed if content changed"""
        existing = self.get_document(doc_id)
        if not existing:
            return False
        
        # Merge updates
        updated_doc = {**existing, **updates, "updated_at": datetime.utcnow().isoformat()}
        
        # Re-embed if title or content changed
        if "title" in updates or "content" in updates:
            text_for_embedding = f"{updated_doc['title']} {updated_doc['content']}"
            vector = self.embedding_service.encode_single(text_for_embedding)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload=updated_doc
                    )
                ]
            )
        else:
            # Just update payload
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=updated_doc,
                points=[doc_id]
            )
        
        logger.info(f"Document updated: {doc_id}")
        return True
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[doc_id]
                )
            )
            logger.info(f"Document deleted: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.5,
        filter_category: Optional[str] = None,
        filter_source_type: Optional[str] = None,
        filter_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for documents similar to the query"""
        query_vector = self.embedding_service.encode_single(query)
        
        # Build filter conditions
        conditions = []
        if filter_category:
            conditions.append(
                FieldCondition(field_name="category", match=MatchValue(value=filter_category))
            )
        if filter_source_type:
            conditions.append(
                FieldCondition(field_name="source_type", match=MatchValue(value=filter_source_type))
            )
        if filter_tags:
            for tag in filter_tags:
                conditions.append(
                    FieldCondition(field_name="tags", match=MatchValue(value=tag))
                )
        
        search_filter = Filter(must=conditions) if conditions else None
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True
        )
        
        return [
            {
                "id": str(r.id),
                "score": r.score,
                **r.payload
            }
            for r in results
        ]
    
    def find_similar(
        self,
        doc_id: str,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Find documents similar to a given document"""
        # Get the document's vector
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[doc_id],
            with_vectors=True
        )
        
        if not points:
            return []
        
        vector = points[0].vector
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit + 1,  # +1 to account for the document itself
            score_threshold=score_threshold,
            with_payload=True
        )
        
        # Exclude the original document
        return [
            {
                "id": str(r.id),
                "score": r.score,
                **r.payload
            }
            for r in results
            if str(r.id) != doc_id
        ][:limit]
    
    def get_relationships(
        self,
        doc_ids: List[str],
        similarity_threshold: float = 0.6
    ) -> Tuple[List[Dict], List[Dict]]:
        """Get relationship graph for given documents"""
        nodes = []
        edges = []
        seen_edges = set()
        
        # Get all documents
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=doc_ids,
            with_vectors=True,
            with_payload=True
        )
        
        # Create nodes
        for point in points:
            nodes.append({
                "id": str(point.id),
                "title": point.payload.get("title", ""),
                "category": point.payload.get("category"),
                "source_type": point.payload.get("source_type")
            })
        
        # Find relationships between documents
        for point in points:
            similar = self.client.search(
                collection_name=self.collection_name,
                query_vector=point.vector,
                limit=10,
                score_threshold=similarity_threshold,
                with_payload=True
            )
            
            for sim in similar:
                if str(sim.id) != str(point.id) and str(sim.id) in doc_ids:
                    edge_key = tuple(sorted([str(point.id), str(sim.id)]))
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({
                            "source": str(point.id),
                            "target": str(sim.id),
                            "weight": sim.score
                        })
        
        return nodes, edges
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        info = self.client.get_collection(self.collection_name)
        
        # Get all documents for aggregation
        all_points, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True
        )
        
        categories = {}
        source_types = {}
        tags = {}
        
        for point in all_points:
            cat = point.payload.get("category")
            if cat:
                categories[cat] = categories.get(cat, 0) + 1
            
            st = point.payload.get("source_type")
            if st:
                source_types[st] = source_types.get(st, 0) + 1
            
            for tag in point.payload.get("tags", []):
                tags[tag] = tags.get(tag, 0) + 1
        
        return {
            "total_documents": info.points_count,
            "categories": categories,
            "source_types": source_types,
            "tags": tags
        }
    
    def get_all_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all documents with pagination"""
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            offset=offset,
            with_payload=True
        )
        
        return [
            {
                "id": str(point.id),
                **point.payload
            }
            for point in points
        ]


# Global instance
_qdrant_service = None


def get_qdrant_service() -> QdrantService:
    """Get or create the Qdrant service singleton"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service
