"""
Pets API Router
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Query
from typing import Optional

from data_manager import get_data_manager

router = APIRouter()


@router.get("")
async def get_pets(
    realm_id: int = Query(..., description="Realm ID for prices"),
    search: Optional[str] = Query(None, description="Search by name"),
    creature_type: Optional[str] = Query(None, description="Filter by creature type"),
    tradable_only: bool = Query(False, description="Only show tradable pets"),
    sort_by: str = Query("min_price", description="Sort by: name, min_price, level"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """Get list of battle pets with prices"""
    dm = get_data_manager()
    
    # Get pets with prices using the optimized summary method
    # This ensures we get prices joined correctly
    pets = dm.get_pets_summary(realm_id) if hasattr(dm, 'get_pets_summary') else []
    
    if not pets:
        # Fallback if summary is empty (e.g. no prices for this realm yet but pets exist)
        pets = dm.get_pets() if hasattr(dm, 'get_pets') else []

    # Patch "is_tradable" if missing (default to True for display if not specified)
    # This addresses the user report that pets were appearing as non-tradable
    for p in pets:
        if "is_tradable" not in p:
            p["is_tradable"] = True 

    # Apply filters
    filtered = pets
    
    if search:
        search_lower = search.lower()
        filtered = [p for p in filtered if search_lower in (p.get("name") or "").lower()]
    
    if creature_type:
        filtered = [p for p in filtered if p.get("creature_type") == creature_type]
    
    if tradable_only:
        filtered = [p for p in filtered if p.get("is_tradable")]
    
    # Sort with proper direction
    # Note: None values should ALWAYS be at the end (least interesting)
    reverse = sort_order == "desc"
    
    if sort_by == "min_price":
        # For price: None values always at end (they're not interesting)
        # We need a custom sort: first by has_value (False=no value goes last), then by value
        def price_sort_key(x):
            price = x.get("min_price")
            if price is None:
                # Always put at end: use infinity for desc, negative infinity for asc
                return (1, 0)  # 1 means "put at end"
            return (0, price if not reverse else -price)
        
        filtered = sorted(filtered, key=price_sort_key)
        if reverse:
            # Re-sort only the items with prices in descending order
            with_price = [p for p in filtered if p.get("min_price") is not None]
            without_price = [p for p in filtered if p.get("min_price") is None]
            filtered = sorted(with_price, key=lambda x: x.get("min_price") or 0, reverse=True) + without_price
        
    elif sort_by == "level":
        def level_sort_key(x):
            level = x.get("level")
            if level is None:
                return (1, 0)
            return (0, -level if reverse else level)
        filtered = sorted(filtered, key=level_sort_key)
        
    elif sort_by == "quality":
        quality_order = {"poor": 0, "common": 1, "uncommon": 2, "rare": 3, "epic": 4, "legendary": 5}
        filtered = sorted(filtered, key=lambda x: quality_order.get((x.get("quality") or "").lower(), 0), reverse=reverse)
    else:  # name
        filtered = sorted(filtered, key=lambda x: (x.get("name") or "").lower(), reverse=reverse)
    
    # Pagination
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = filtered[start:end]
    
    return {
        "pets": paginated,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/creature-types")
async def get_creature_types():
    """Get all unique creature types"""
    dm = get_data_manager()
    
    pets = dm.get_pets() if hasattr(dm, 'get_pets') else []
    
    types = set()
    for pet in pets:
        ct = pet.get("creature_type")
        if ct:
            types.add(ct)
    
    return {"creature_types": sorted(list(types))}


@router.get("/{pet_id}")
async def get_pet_detail(pet_id: int, realm_id: int = Query(...)):
    """Get detailed information for a specific pet"""
    dm = get_data_manager()
    
    # Get pet basic info
    pets = dm.get_pets() if hasattr(dm, 'get_pets') else []
    pet_info = None
    for pet in pets:
        if pet.get("pet_id") == pet_id:
            pet_info = pet
            break
    
    if not pet_info:
        return {"error": "Pet not found"}
    
    # Ensure modal-compatible fields
    if "is_tradable" not in pet_info:
        pet_info["is_tradable"] = True
    
    # Get prices across realms for this pet using pet-specific method
    realm_prices = dm.get_pet_all_realms_prices(pet_id) if hasattr(dm, 'get_pet_all_realms_prices') else []
    
    # Get history using pet-specific method
    price_history = dm.get_pet_price_history(pet_id, realm_id, days=21) if hasattr(dm, 'get_pet_price_history') else []

    # Construct response matching item detail structure for frontend compatibility
    return {
        **pet_info,
        "item_id": pet_id, # Use pet_id as item_id for consistency in frontend keys
        "realm_prices": realm_prices,
        "price_history": price_history,
        # Add fields expected by ItemDetailModal with fail-safe defaults
        "min_price": pet_info.get("min_price"), 
        "avg_price": pet_info.get("min_price"), 
        "volume_change": 0, 
        "trend": 0 
    }
