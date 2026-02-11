"""MindsDB UI Backend - FastAPI Application"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import datasources, query

app = FastAPI(
    title="MindsDB UI API",
    description="Backend API for MindsDB Data Source Management UI",
    version="1.0.0"
)

# CORS middleware for Vue.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "*"  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(datasources.router, prefix="/api")
app.include_router(query.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MindsDB UI API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
