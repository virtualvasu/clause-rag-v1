"""
Clause FastAPI Application
Main entry point for the REST API server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Clause RAG API",
    description="Hybrid GraphRAG system for Indian startup law",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "clause-api",
        "version": "0.1.0"
    }

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Clause RAG API - Legal clarity for Indian startups",
        "docs": "/docs",
        "health": "/health"
    }

# TODO: Add route imports
# from clause.api.routes import query, ingest
# app.include_router(query.router, prefix="/api/v1", tags=["queries"])
# app.include_router(ingest.router, prefix="/api/v1", tags=["ingestion"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
