from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.backend.config import settings
from apps.backend.core.logging import setup_logging
from apps.backend.lifespan import lifespan
from apps.backend.routers import health


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    """
    setup_logging()

    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from apps.backend.exceptions import (
        custom_http_exception_handler,
        domain_exception_handler,
        global_exception_handler,
        validation_exception_handler,
    )
    from apps.backend.middleware.request_context import RequestContextMiddleware
    from packages.execution_engine.domain.exceptions import DomainException

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
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # Include routers
    # The health check is typically mounted at the root rather than under api/v1 prefix
    app.include_router(health.router)

    from apps.backend.routers import (
        auth,
        benchmarks,
        datasets,
        evaluation,
        executions,
        internal_workers,
        organizations,
        projects,
        reporting,
        system,
    )

    # We will mount these under /api/v1 for the actual domain routes
    api_v1 = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(organizations.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(projects.org_projects_router, prefix="/api/v1")
    app.include_router(datasets.router, prefix="/api/v1")
    app.include_router(benchmarks.project_benchmarks_router, prefix="/api/v1")
    app.include_router(benchmarks.benchmarks_router, prefix="/api/v1")
    app.include_router(benchmarks.benchmark_versions_router, prefix="/api/v1")
    app.include_router(executions.benchmark_executions_router, prefix="/api/v1")
    app.include_router(executions.executions_router, prefix="/api/v1")
    app.include_router(internal_workers.workers_router, prefix="/api/v1/internal/workers")
    app.include_router(evaluation.router, prefix="/api/v1")
    app.include_router(reporting.router, prefix="/api/v1")
    app.include_router(system.router, prefix="/api/v1")

    return app


app = create_app()
