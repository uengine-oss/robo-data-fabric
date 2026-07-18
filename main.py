"""Data Fabric connection and real-data access API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import datasources, query, tables
from observability import configure_logging
from settings import settings

configure_logging()

app = FastAPI(
    title="Robo Data Fabric API",
    description="Data source connections and MindsDB-backed query/sample access",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasources.router, prefix="/api")
app.include_router(tables.router, prefix="/api")
app.include_router(query.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Robo Data Fabric API",
        "docs": "/docs",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
