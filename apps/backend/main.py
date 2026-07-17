from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.backend.config import settings
from apps.backend.lifespan import lifespan
from apps.backend.routers import health
from apps.backend.core.logging import setup_logging

def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    """
    setup_logging()
    
    from apps.backend.middleware.request_context import RequestContextMiddleware
    from apps.backend.exceptions import (
        custom_http_exception_handler,
        validation_exception_handler,
        global_exception_handler
    )
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from fastapi.exceptions import RequestValidationError

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Atlas Backend API serving evaluation and benchmark orchestration.",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust this in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # Include routers
    # The health check is typically mounted at the root rather than under api/v1 prefix
    app.include_router(health.router)

    from apps.backend.routers import organizations, projects, auth, datasets, benchmarks, executions, evaluation, system
    
    # We will mount these under /api/v1 for the actual domain routes
    api_v1 = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(organizations.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(projects.org_projects_router, prefix="/api/v1")
    app.include_router(datasets.router, prefix="/api/v1")
    app.include_router(benchmarks.router, prefix="/api/v1")
    app.include_router(executions.router, prefix="/api/v1")
    app.include_router(evaluation.router, prefix="/api/v1")
    app.include_router(system.router, prefix="/api/v1")

    return app

app = create_app()
