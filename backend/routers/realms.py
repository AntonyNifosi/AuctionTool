"""
Realms API Router
"""
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException
from typing import List

from ..data_manager import get_data_manager
from ..blizzard_api import get_api, BlizzardAPIError
from backend.schemas import RealmResponse

router = APIRouter()


@router.get("", response_model=List[RealmResponse])
async def get_realms():
    """Get all available realms/servers"""
    dm = get_data_manager()
    
    # Try to get from database first
    cached_realms = dm.get_realms()
    
    if cached_realms:
        return [
            RealmResponse(
                id=realm["id"],
                name=realm["name"],
                population=realm.get("population"),
                region=realm.get("region")
            )
            for realm in cached_realms
        ]
    
    # If not cached, fetch from API
    try:
        api = get_api()
        realms = api.get_all_realms_with_names()
        
        # Save to database
        for realm in realms:
            dm.save_realm(realm["id"], realm["name"])
        
        return [
            RealmResponse(
                id=realm["id"],
                name=realm["name"]
            )
            for realm in realms
        ]
    except BlizzardAPIError as e:
        raise HTTPException(status_code=503, detail=f"Blizzard API error: {str(e)}")


@router.get("/{realm_id}")
async def get_realm(realm_id: int):
    """Get details for a specific realm"""
    dm = get_data_manager()
    realms = dm.get_realms()
    
    for realm in realms:
        if realm["id"] == realm_id:
            return RealmResponse(
                id=realm["id"],
                name=realm["name"],
                population=realm.get("population"),
                region=realm.get("region")
            )
    
    raise HTTPException(status_code=404, detail="Realm not found")
