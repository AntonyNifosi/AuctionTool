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
    sort_by: str = Query("name", description="Sort by: name, price, quality"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """Get list of battle pets with prices"""
    dm = get_data_manager()
    
    # Get pets with prices
    pets = dm.get_pets_summary(realm_id) if hasattr(dm, 'get_pets_summary') else []
    
    if not pets:
        # Try to get basic pet list
        pets = dm.get_pets() if hasattr(dm, 'get_pets') else []
    
    # Apply filters
    filtered = pets
    
    if search:
        search_lower = search.lower()
        filtered = [p for p in filtered if search_lower in (p.get("name") or "").lower()]
    
    if creature_type:
        filtered = [p for p in filtered if p.get("creature_type") == creature_type]
    
    if tradable_only:
        filtered = [p for p in filtered if p.get("is_tradable")]
    
    # Sort
    if sort_by == "price":
        filtered = sorted(filtered, key=lambda x: x.get("min_price") or float('inf'))
    elif sort_by == "quality":
        quality_order = {"poor": 0, "common": 1, "uncommon": 2, "rare": 3, "epic": 4, "legendary": 5}
        filtered = sorted(filtered, key=lambda x: quality_order.get((x.get("quality") or "").lower(), 0), reverse=True)
    else:
        filtered = sorted(filtered, key=lambda x: (x.get("name") or "").lower())
    
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
    
    # Get pet info
    pets = dm.get_pets() if hasattr(dm, 'get_pets') else []
    pet_info = None
    for pet in pets:
        if pet.get("pet_id") == pet_id:
            pet_info = pet
            break
    
    if not pet_info:
        return {"error": "Pet not found"}
    
    # Get prices across realms
    prices = dm.get_pet_prices_by_realm(pet_id) if hasattr(dm, 'get_pet_prices_by_realm') else []
    
    return {
        **pet_info,
        "realm_prices": prices
    }
