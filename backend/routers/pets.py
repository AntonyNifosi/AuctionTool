"""
Pets API Router
"""
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Query
from typing import Optional, List

from ..data_manager import get_data_manager

router = APIRouter()


@router.get("")
async def get_pets(
    realm_id: int = Query(..., description="Realm ID for prices"),
    search: Optional[str] = Query(None, description="Search by name"),
    source: Optional[List[str]] = Query(None, description="Filter by source (one or more)"),
    creature_type: Optional[str] = Query(None, description="Filter by creature type"),
    tradable_only: bool = Query(False, description="Only show tradable pets"),
    sort_by: str = Query("min_price", description="Sort by: name, min_price, level, quality"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """Get list of battle pets with prices"""
    dm = get_data_manager()
    
    offset = (page - 1) * page_size
    
    # Optimized call: SQL-based filtering, sorting, pagination
    pets, total_count = dm.get_pets_summary(
        realm_id=realm_id,
        search_query=search,
        source_filter=source,
        creature_type=creature_type,
        tradable_only=tradable_only,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=page_size,
        offset=offset
    )
    
    # Patch "is_tradable" if missing (should be handled by SQL COALESCE now, but keeping for safety if dict keys missing)
    for p in pets:
        if "is_tradable" not in p:
            p["is_tradable"] = True 

    return {
        "pets": pets,
        "total": total_count,
        "page": page,
        "page_size": page_size
    }


@router.get("/creature-types")
async def get_creature_types():
    """Get all unique creature types"""
    dm = get_data_manager()
    
    # Optimization: Use SQL DISTINCT instead of loading all pets?
    # Keeping old method for now as it uses get_pets() which is now optimized? 
    # Wait, get_pets() in dm was "SELECT * FROM pets". 
    # Let's keep existing logic using get_pets() which is simple SELECT * FROM pets (cheap enough if not joined)
    # But wait, get_pets() fetches all. If we have 1000s pets, it's ok.
    
    pets = dm.get_pets() if hasattr(dm, 'get_pets') else []
    
    types = set()
    for pet in pets:
        ct = pet.get("creature_type")
        if ct:
            types.add(ct)
    
    return {"creature_types": sorted(list(types))}


@router.get("/sources")
async def get_pet_sources():
    """Get all unique pet sources"""
    dm = get_data_manager()
    
    pets = dm.get_pets() if hasattr(dm, 'get_pets') else []
    
    sources = set()
    for pet in pets:
        src = pet.get("source")
        if src and src.strip():
            sources.add(src.strip())
    
    return {"sources": sorted(list(sources))}


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

    # Find price for the requested realm to return correct min_price (3d or current)
    # This prevents the UI from "flickering" from 3d price (collection) to current price (detail api)
    current_realm_price = None
    for rp in realm_prices:
        if rp["realm_id"] == realm_id:
            # PRIORITIZE min_price_3d similar to Best Servers and Collection logic
            current_realm_price = rp.get("min_price_3d") or rp.get("min_price")
            break
            
    # Default to pet_info price if realm specific not found (fallback)
    final_price = current_realm_price if current_realm_price is not None else pet_info.get("min_price")

    # Construct response matching item detail structure for frontend compatibility
    return {
        **pet_info,
        "item_id": pet_id, # Use pet_id as item_id for consistency in frontend keys
        "realm_prices": realm_prices,
        "price_history": price_history,
        # Add fields expected by ItemDetailModal with fail-safe defaults
        "min_price": final_price, 
        "avg_price": final_price, 
        "volume_change": 0, 
        "trend": 0 
    }


@router.get("/{pet_id}/best-servers")
async def get_pet_best_servers(pet_id: int, days: int = Query(7, ge=1, le=30)):
    """Get best servers to sell this pet with scoring"""
    dm = get_data_manager()
    
    # Get all realm prices for this pet
    realm_prices = dm.get_pet_all_realms_prices(pet_id) if hasattr(dm, 'get_pet_all_realms_prices') else []
    
    # Filter out servers without price and Russian servers
    servers = [r for r in realm_prices if r.get("min_price") and r.get("region") != "ru_RU"]
    
    if not servers:
        return {"pet_id": pet_id, "servers": []}
    
    # Population scoring
    population_scores = {
        "FULL": 1.0,
        "HIGH": 0.8,
        "MEDIUM": 0.6,
        "LOW": 0.4,
        "NEW_PLAYERS": 0.3,
    }
    
    # Get min/max for normalization (Use 3D price to avoid spikes)
    prices = [s.get("min_price_3d") or s["min_price"] for s in servers]
    quantities = [s.get("total_quantity", 0) or 0 for s in servers]
    
    max_price = max(prices) if prices else 1
    min_price = min(prices) if prices else 0
    # For pets, lower quantity = rarer = better to sell (inverse)
    max_qty = max(quantities) if quantities else 1
    min_qty = min(quantities) if quantities else 0
    
    # Calculate score for each server
    results = []
    for s in servers:
        # Use 3d price for scoring if available
        price = s.get("min_price_3d") or s["min_price"]
        current_price = s["min_price"]
        qty = s.get("total_quantity", 0) or 0
        pop = s.get("population") or "UNKNOWN"
        
        # Normalize price (higher = better for selling)
        price_norm = (price - min_price) / (max_price - min_price) if max_price != min_price else 0.5
        
        # Normalize quantity (lower = rarer = better for selling, so invert)
        qty_norm = 1 - ((qty - min_qty) / (max_qty - min_qty)) if max_qty != min_qty else 0.5
        
        pop_score = population_scores.get(pop, 0.5)
        
        # Score: Prix 40%, Rareté 40%, Population 20%
        score = (price_norm * 0.4) + (qty_norm * 0.4) + (pop_score * 0.2)
        
        results.append({
            "realm_name": s.get("realm_name"),
            "population": pop,
            "region": s.get("region"),
            "min_price": price, # Display the used price (3d min) OR send both? Let's send 3d min as min_price for now to fix ranking expectation
            "current_price": current_price, # Send current separately if needed
            "total_quantity": qty,
            "score": round(score * 100, 1)
        })
    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {"pet_id": pet_id, "servers": results}
