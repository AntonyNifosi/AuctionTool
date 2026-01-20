"""
Update API Router - Background data updates
"""
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, BackgroundTasks
from datetime import datetime

from ..data_manager import get_data_manager
from ..update_manager import UpdateManager

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
    """Get current update status"""
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
async def start_update(force: bool = False, priority_realm_id: int = None):
    """Start a background data update"""
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
async def stop_update():
    """Stop the current update"""
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
