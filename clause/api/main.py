"""
FastAPI application factory.
Run with: uvicorn clause.api.main:app --reload --port 8000
Docs at:  http://localhost:8000/docs
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Clause API",
        description=(
            "Legal Q&A for Indian startups. "
            "Hybrid GraphRAG over Companies Act, SEBI Regulations, and DPIIT Guidelines."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Allow Next.js dev server (3000) and any other origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from clause.api.routes.query import router
    app.include_router(router, tags=["Query"])

    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Clause API", "docs": "/docs", "health": "/health"}

    return app


app = create_app()
