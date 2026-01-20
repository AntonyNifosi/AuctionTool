"""
Prices API Router
"""
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Query
from typing import Optional

from ..data_manager import get_data_manager

router = APIRouter()


@router.get("/{realm_id}/{item_id}")
async def get_price_data(
    realm_id: int,
    item_id: int,
    days: int = Query(21, ge=1, le=90, description="Number of days of history")
):
    """Get price history for an item on a specific realm"""
    dm = get_data_manager()
    
    # Get current price
    current = dm.get_current_price(item_id, realm_id)
    
    # Get history
    history = dm.get_price_history(item_id, realm_id, days=days)
    
    # Get trend
    trend = dm.calculate_trend(item_id, realm_id)
    
    # Get volume change
    volume_change = dm.calculate_weekly_volume_change(item_id, realm_id)
    
    return {
        "item_id": item_id,
        "realm_id": realm_id,
        "current": {
            "min_price": current.get("min_price") if current else None,
            "avg_price": current.get("avg_price") if current else None,
            "total_quantity": current.get("total_quantity") if current else None,
            "auction_count": current.get("auction_count") if current else None,
            "recorded_at": str(current.get("recorded_at")) if current and current.get("recorded_at") else None
        } if current else None,
        "trend": trend,
        "volume_change": volume_change,
        "history": [
            {
                "recorded_at": str(h["recorded_at"]),
                "min_price": h["min_price"],
                "avg_price": h["avg_price"],
                "total_quantity": h["total_quantity"],
                "auction_count": h["auction_count"]
            }
            for h in history
        ]
    }


@router.get("/{realm_id}/{item_id}/best-servers")
async def get_best_servers(
    realm_id: int,
    item_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Get best servers to sell this item"""
    dm = get_data_manager()
    
    best_servers = dm.get_best_servers_data(item_id, days=days)
    
    return {
        "item_id": item_id,
        "servers": best_servers
    }
