"""Data Fabric connection and real-data access API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .http import datasource_endpoints, query_endpoints
from .system.settings import settings

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

app.include_router(datasource_endpoints.router, prefix="/api")
app.include_router(query_endpoints.router, prefix="/api")


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
