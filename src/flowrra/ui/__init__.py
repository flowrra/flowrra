"""UI adapters for mounting Flowrra into web frameworks.

This module provides optional UI adapters that allow mounting Flowrra's
management interface into existing web applications. The adapters are
framework-specific and have NO dependencies in the core Flowrra package.

Available Adapters:
    - FastAPI: flowrra.ui.fastapi.create_router()
    - Flask: flowrra.ui.flask.create_blueprint()
    - Django: flowrra.ui.django.get_urls()

Important:
    - Core Flowrra has ZERO web framework dependencies
    - UI adapters are optional imports
    - Users install only what they need:
        pip install flowrra[ui-fastapi]
        pip install flowrra[ui-flask]
        pip install flowrra[ui-django]

Example (FastAPI):
    from fastapi import FastAPI
    from flowrra import Flowrra
    from flowrra.ui.fastapi import create_router

    app = FastAPI()
    flowrra = Flowrra.from_urls()

    # Mount Flowrra UI
    app.include_router(
        create_router(flowrra),
        prefix="/flowrra"
    )

Example (Flask):
    from flask import Flask
    from flowrra import Flowrra
    from flowrra.ui.flask import create_blueprint

    app = Flask(__name__)
    flowrra = Flowrra.from_urls()

    # Mount Flowrra UI
    app.register_blueprint(
        create_blueprint(flowrra),
        url_prefix="/flowrra"
    )
"""

from flowrra.ui.base import (
    BaseUIAdapter,
    Formatter,
    UIService,
    ScheduleService,
)

__all__ = [
    "BaseUIAdapter",
    "Formatter",
    "UIService",
    "ScheduleService",
]
