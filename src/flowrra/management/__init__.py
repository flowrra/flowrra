"""Management API for querying Flowrra state.

This module provides a pure Python API for querying and managing Flowrra
applications. It has NO web framework dependencies and can be used by:
- CLI tools
- Web UI adapters (FastAPI, Flask, Django)
- Monitoring scripts
- Testing utilities

Example:
    from flowrra import Flowrra
    from flowrra.management import FlowrraManager

    app = Flowrra.from_urls()
    manager = FlowrraManager(app)

    # Query system state
    stats = await manager.get_stats()
    tasks = await manager.list_registered_tasks()
    schedules = await manager.list_schedules()
"""

from flowrra.management.manager import FlowrraManager

__all__ = ["FlowrraManager"]
