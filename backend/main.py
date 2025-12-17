from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from routers import documents, search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Medya Takip Merkezi - Vector Database",
    description="Qdrant tabanlı semantik arama ve doküman yönetimi API'si",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router)
app.include_router(search.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mtm-vector-db"}


@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "Medya Takip Merkezi",
        "description": "Vector Database API",
        "version": "1.0.0",
        "endpoints": {
            "documents": "/api/documents",
            "search": "/api/search",
            "docs": "/api/docs"
        }
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Medya Takip Merkezi Vector Database API...")
    
    # Initialize services (this will load the embedding model)
    from services.qdrant_service import get_qdrant_service
    try:
        service = get_qdrant_service()
        logger.info("Qdrant service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Medya Takip Merkezi Vector Database API...")
