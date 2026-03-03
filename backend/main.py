"""
FastAPI Backend for WoW Housing Price Tracker
Provides REST API endpoints for the React frontend
"""
import sys
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path to import existing modules
# Add parent directory to path to import existing modules
# sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routers import realms, items, prices, profits, pets, update, collection, auth

# Background scheduler state
_scheduler_task = None
_scheduler_running = False
SCAN_INTERVAL_HOURS = 1  # Scan every hour
AUTO_SCAN_ENABLED = True  # Re-enabled after performance optimization (batch inserts)


async def auto_scan_scheduler():
    """Background task that triggers market scans automatically every hour"""
    global _scheduler_running
    _scheduler_running = True
    
    # Import here to avoid circular imports
    from .routers.update import get_update_manager
    from .data_manager import get_data_manager
    
    print(f"[Auto-Scan] Scheduler started - scans every {SCAN_INTERVAL_HOURS} hour(s)")
    
    while _scheduler_running:
        try:
            mgr = get_update_manager()
            dm = get_data_manager()
            
            # Check if we need to run a scan
            last_update = dm.get_last_price_update()
            should_scan = False
            
            if last_update is None:
                should_scan = True
                print("[Auto-Scan] No previous scan found, starting initial scan")
            else:
                # Check if last update was more than SCAN_INTERVAL_HOURS ago
                # Use UTC for comparison since DB stores UTC timestamps
                now_utc = datetime.utcnow()
                # Ensure last_update is timezone-naive for comparison
                if last_update.tzinfo is not None:
                    last_update = last_update.replace(tzinfo=None)
                hours_since_update = (now_utc - last_update).total_seconds() / 3600
                if hours_since_update >= SCAN_INTERVAL_HOURS:
                    should_scan = True
                    print(f"[Auto-Scan] Last scan was {hours_since_update:.1f}h ago, starting new scan")
            
            if should_scan and not mgr.is_running():
                print(f"[Auto-Scan] Triggering automatic market scan at {datetime.now().strftime('%H:%M:%S')}")
                mgr.start_background_update(force=False)
            
            # Wait 5 minutes before checking again
            await asyncio.sleep(300)
            
        except Exception as e:
            print(f"[Auto-Scan] Error in scheduler: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global _scheduler_task, _scheduler_running
    
    # Startup: Start the auto-scan scheduler only if enabled
    # Also initialize database once here
    from .data_manager import get_data_manager
    dm = get_data_manager()
    dm.initialize_database()
    print("[Startup] Database initialized")
    
    if AUTO_SCAN_ENABLED:
        print("[Startup] Starting auto-scan scheduler...")
        _scheduler_task = asyncio.create_task(auto_scan_scheduler())
    else:
        print("[Startup] Auto-scan scheduler DISABLED - use manual refresh button")
    
    yield
    
    # Shutdown: Stop the scheduler
    if _scheduler_task:
        print("[Shutdown] Stopping auto-scan scheduler...")
        _scheduler_running = False
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="WoW Housing Price Tracker API",
    description="API pour suivre les prix des items de housing World of Warcraft",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(collection.router, prefix="/api/collection", tags=["Collection"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/")
async def root():
    return {"message": "WoW Housing Price Tracker API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/scheduler/status")
async def scheduler_status():
    """Get auto-scan scheduler status"""
    from backend.routers.update import get_update_manager
    from data_manager import get_data_manager
    
    mgr = get_update_manager()
    dm = get_data_manager()
    last_update = dm.get_last_price_update()
    
    next_scan = None
    if last_update:
        next_scan_time = last_update + timedelta(hours=SCAN_INTERVAL_HOURS)
        next_scan = str(next_scan_time)
    
    return {
        "scheduler_running": _scheduler_running,
        "scan_interval_hours": SCAN_INTERVAL_HOURS,
        "last_scan": str(last_update) if last_update else None,
        "next_scan_scheduled": next_scan,
        "update_in_progress": mgr.is_running()
    }
