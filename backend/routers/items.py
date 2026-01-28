"""
Items API Router
"""
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Query
from typing import List, Optional

from ..data_manager import get_data_manager
from backend.schemas import ItemSummary, ItemListResponse

router = APIRouter()


@router.get("", response_model=ItemListResponse)
async def get_items(
    realm_id: int = Query(..., description="Realm ID for price data"),
    search: Optional[str] = Query(None, description="Search by item name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort_by: Optional[str] = Query("name", description="Sort field: name, min_price, trend"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page")
):
    """Get paginated list of items with prices and metrics"""
    dm = get_data_manager()
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Optimized call: Pass all filters and sorting to DataManager (SQL)
    items, total_count = dm.get_items_summary(
        realm_id, 
        search_query=search, 
        category=category,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=page_size, 
        offset=offset
    )

    return ItemListResponse(
        items=[ItemSummary(**item) for item in items],
        total=total_count,
        page=page,
        page_size=page_size
    )


@router.get("/categories")
async def get_categories():
    """Get all unique categories"""
    dm = get_data_manager()
    items = dm.get_housing_items()
    
    categories = set()
    for item in items:
        cat = item.get("category") or "Autre"
        categories.add(cat)
    
    return {"categories": sorted(list(categories))}


@router.get("/{item_id}")
async def get_item_detail(item_id: int, realm_id: int = Query(...)):
    """Get detailed information for a specific item"""
    dm = get_data_manager()
    
    # Get basic item info
    items = dm.get_housing_items()
    item_info = None
    for item in items:
        if item["item_id"] == item_id:
            item_info = item
            break
    
    if not item_info:
        return {"error": "Item not found"}
    
    # Get current price
    current_price = dm.get_current_price(item_id, realm_id)
    
    # Get price history
    price_history = dm.get_price_history(item_id, realm_id, days=21)
    
    # Get trend
    trend = dm.calculate_trend(item_id, realm_id)
    
    # Get volume change
    volume_change = dm.calculate_weekly_volume_change(item_id, realm_id)
    
    return {
        "item_id": item_id,
        "name": item_info.get("name"),
        "icon_url": item_info.get("icon_url"),
        "category": item_info.get("category"),
        "subcategory": item_info.get("subcategory"),
        "current_price": current_price.get("min_price") if current_price else None,
        "avg_price": current_price.get("avg_price") if current_price else None,
        "trend": trend,
        "sales_3d": dm.get_estimated_sales_3d(item_id, realm_id),
        "min_price_3d": dm.get_min_price_3d(item_id, realm_id),
        "volume_change": volume_change,
        "price_history": [
            {
                "recorded_at": str(h["recorded_at"]),
                "min_price": h["min_price"],
                "avg_price": h["avg_price"],
                "total_quantity": h["total_quantity"],
                "auction_count": h["auction_count"]
            }
            for h in price_history
        ],
        "reagents": dm.get_recipe_reagents_details(item_id, realm_id)
    }


@router.get("/{item_id}/realms")
async def get_item_prices_by_realm(item_id: int):
    """Get prices for an item across all realms"""
    dm = get_data_manager()
    
    prices = dm.get_all_realms_prices(item_id)
    
    return {
        "item_id": item_id,
        "realm_prices": [
            {
                "realm_id": p["realm_id"],
                "realm_name": p["realm_name"],
                "region": p.get("region"),
                "min_price": p["min_price"],
                "min_price_3d": p.get("min_price_3d"),
                "avg_price": p["avg_price"],
                "total_quantity": p["total_quantity"],
                "recorded_at": str(p["recorded_at"]) if p.get("recorded_at") else None,
                "sales_3d": p.get("sales_3d", 0)
            }
            for p in prices
        ]
    }
