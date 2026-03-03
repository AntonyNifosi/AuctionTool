"""
Update API Router - Background data updates
Protected: start/stop/sync-recipes require admin auth
"""
from fastapi import APIRouter, Depends, Header
from typing import Optional
from datetime import datetime

from ..data_manager import get_data_manager
from ..update_manager import UpdateManager
from .auth import require_admin

router = APIRouter()

# Singleton update manager
_update_manager = None

def get_update_manager():
    global _update_manager
    if _update_manager is None:
        _update_manager = UpdateManager()
    return _update_manager


@router.get("/status")
async def get_update_status():
    """Get current update status (public - no auth required)"""
    mgr = get_update_manager()
    
    # Only read DB when NOT running to avoid lock contention with scan writes
    last_update = None
    if not mgr.is_running():
        dm = get_data_manager()
        last_update = dm.get_last_price_update()
    else:
        # Use cached value from UpdateManager
        last_update = mgr.last_update_time
    
    return {
        "is_running": mgr.is_running(),
        "progress": mgr.progress if hasattr(mgr, 'progress') else 0,
        "status_message": mgr.status_message if hasattr(mgr, 'status_message') else "",
        "last_update_time": str(last_update) if last_update else None
    }


@router.post("/start")
async def start_update(
    force: bool = False,
    priority_realm_id: int = None,
    _admin: bool = Depends(require_admin)
):
    """Start a background data update (admin only)"""
    mgr = get_update_manager()
    
    if mgr.is_running():
        return {
            "success": False,
            "message": "Update already in progress"
        }
    
    mgr.start_background_update(force=force, priority_realm_id=priority_realm_id)
    
    return {
        "success": True,
        "message": "Update started"
    }


@router.post("/stop")
async def stop_update(_admin: bool = Depends(require_admin)):
    """Stop the current update (admin only)"""
    mgr = get_update_manager()
    
    if not mgr.is_running():
        return {
            "success": False,
            "message": "No update in progress"
        }
    
    mgr.stop_update()
    
    return {
        "success": True,
        "message": "Update stop requested"
    }


@router.post("/sync-recipes")
async def sync_recipes(_admin: bool = Depends(require_admin)):
    """Force recipe re-sync (admin only) - runs in background"""
    mgr = get_update_manager()
    
    if mgr.is_running():
        return {
            "success": False,
            "message": "An update is already in progress. Wait for it to finish."
        }
    
    # Launch recipe sync in background thread
    import threading
    from ..blizzard_api import get_api
    
    def _run_recipe_sync():
        try:
            mgr._is_running = True
            mgr.status_message = "Synchronisation des recettes..."
            mgr.progress = 0.5
            
            api = get_api()
            dm = get_data_manager()
            housing_item_ids = dm.get_housing_item_ids()
            
            mgr._sync_recipes(api, dm, housing_item_ids)
            
            mgr.status_message = "Sync recettes terminée !"
            mgr.progress = 1.0
            mgr.last_update_time = datetime.now()
        except Exception as e:
            mgr.status_message = f"Erreur sync recettes: {e}"
            mgr.last_error = str(e)
        finally:
            mgr._is_running = False
    
    thread = threading.Thread(target=_run_recipe_sync)
    thread.daemon = True
    thread.start()
    
    return {
        "success": True,
        "message": "Recipe sync started"
    }
