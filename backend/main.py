"""
FastAPI Backend for WoW Housing Price Tracker
Provides REST API endpoints for the React frontend
"""
import sys
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import realms, items, prices, profits, pets, update

app = FastAPI(
    title="WoW Housing Price Tracker API",
    description="API pour suivre les prix des items de housing World of Warcraft",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(realms.router, prefix="/api/realms", tags=["Realms"])
app.include_router(items.router, prefix="/api/items", tags=["Items"])
app.include_router(prices.router, prefix="/api/prices", tags=["Prices"])
app.include_router(profits.router, prefix="/api/profits", tags=["Profits"])
app.include_router(pets.router, prefix="/api/pets", tags=["Pets"])
app.include_router(update.router, prefix="/api/update", tags=["Update"])


@app.get("/")
async def root():
    return {"message": "WoW Housing Price Tracker API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
