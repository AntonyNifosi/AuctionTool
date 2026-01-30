"""
Collection API Router - Fetch character pets from Battle.net
"""
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..data_manager import get_data_manager
from ..blizzard_api import get_api, BlizzardAPIError

router = APIRouter()


@router.get("/pets")
async def get_character_collection(
    realm_slug: str = Query(..., description="Realm slug (e.g. 'argent-dawn')"),
    character_name: str = Query(..., description="Character name"),
    realm_id: Optional[int] = Query(None, description="Realm ID for price context")
):
    """
    Fetch a character's pet collection from Battle.net API
    and enrich with price data from our database.
    """
    dm = get_data_manager()
    api = get_api()
    
    try:
        # Fetch character pets from Battle.net
        collection_data = api.get_character_pets(realm_slug, character_name)
        
        if not collection_data or "pets" not in collection_data:
            raise HTTPException(
                status_code=404,
                detail=f"Character '{character_name}' not found on '{realm_slug}' or profile is private"
            )
        
        player_pets = collection_data.get("pets", [])
        
        # Get our database pets for enrichment
        db_pets = {p["pet_id"]: p for p in dm.get_pets()}
        
        # Pre-fetch prices if realm_id provided
        summary_map = {}
        if realm_id:
            # Use get_pets_summary to get prices for this specific realm
            # This ensures consistency with the Pets page
            # We need ALL pets, so set a high limit
            summary_pets_list, _ = dm.get_pets_summary(realm_id, limit=5000)
            summary_map = {p["pet_id"]: p for p in summary_pets_list}
        
        # Build response with price data
        result_pets = []
        total_value = 0
        tradable_count = 0
        
        for player_pet in player_pets:
            species = player_pet.get("species", {})
            species_id = species.get("id")
            pet_name = species.get("name", "Unknown")
            quality = player_pet.get("quality", {}).get("name", "-")
            level = player_pet.get("level", 1)
            
            # Get pet info from our database
            db_pet = db_pets.get(species_id, {})
            
            # Determine price
            price = None
            

            
            if species_id:
                if realm_id:
                    # Constant time lookup from pre-fetched map
                    summary_info = summary_map.get(species_id, {})
                    # Prioritize 3-day min price to avoid spikes, fallback to current
                    price = summary_info.get("min_price_3d") or summary_info.get("min_price")
                    sales_3d = summary_info.get("sales_3d", 0)
                else:
                    sales_3d = 0 # Cannot calculate sales without realm context
                    # Fallback to old behavior: minimum price across ALL realms (SLOW & DIFFERENT)
                    prices = dm.get_pet_all_realms_prices(species_id)
                    if prices:
                        # Also prefer 3d price here
                        valid_prices = [p.get("min_price_3d") or p.get("min_price") for p in prices if p.get("min_price")]
                        if valid_prices:
                            price = min(valid_prices)
            
            is_tradable = db_pet.get("is_tradable", False) if db_pet else False
            
            if price and is_tradable:
                total_value += price
                tradable_count += 1
            
            result_pets.append({
                "pet_id": species_id,
                "name": pet_name,
                "level": level,
                "quality": quality,
                "creature_type": db_pet.get("creature_type", "-"),
                "source": db_pet.get("source", "Inconnue"),
                "icon_url": db_pet.get("icon_url"),
                "icon_url": db_pet.get("icon_url"),
                "min_price": price,
                "sales_3d": sales_3d,
                "is_tradable": is_tradable
            })
        
        # Sort by price descending (most valuable first)
        result_pets.sort(key=lambda x: x.get("min_price") or 0, reverse=True)
        
        return {
            "character_name": character_name,
            "realm_slug": realm_slug,
            "pets": result_pets,
            "total_pets": len(result_pets),
            "tradable_count": tradable_count,
            "total_value": total_value
        }
        
    except BlizzardAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Battle.net API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )
