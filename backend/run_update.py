#!/usr/bin/env python
"""
Standalone update script that can be run as a separate process.
This avoids GIL contention with FastAPI's async event loop.
"""
import sys
import os
import json
import time
from pathlib import Path

# Add project root to path
# project_root = Path(__file__).parent
# sys.path.insert(0, str(project_root))

from .update_manager import UpdateManager
from .data_manager import get_data_manager


def main():
    """Run a complete market scan."""
    start_time = time.time()
    
    print(f"[Standalone Update] Starting scan at {time.strftime('%H:%M:%S')}")
    
    # Get command line args
    priority_realm_id = None
    force = False
    
    if len(sys.argv) > 1:
        try:
            priority_realm_id = int(sys.argv[1])
        except ValueError:
            pass
    
    if len(sys.argv) > 2:
        force = sys.argv[2].lower() == 'true'
    
    # Create update manager and run
    mgr = UpdateManager()
    
    # Start the update synchronously (blocking)
    mgr._is_running = True
    mgr.progress = 0.0
    mgr.last_error = None
    mgr.status_message = "Démarrage de la mise à jour..."
    
    try:
        # Run the update process directly (not in a thread)
        mgr._run_process(priority_realm_id)
        
        elapsed = time.time() - start_time
        print(f"[Standalone Update] Completed in {elapsed:.1f}s ({elapsed/60:.1f} min)")
        
        # Write completion status
        status = {
            "success": True,
            "elapsed_seconds": elapsed,
            "message": "Update completed successfully"
        }
        print(json.dumps(status))
        return 0
        
    except Exception as e:
        print(f"[Standalone Update] Error: {e}")
        status = {
            "success": False,
            "error": str(e)
        }
        print(json.dumps(status))
        return 1


if __name__ == "__main__":
    sys.exit(main())
