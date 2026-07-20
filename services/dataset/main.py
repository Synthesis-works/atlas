from fastapi import FastAPI
from .api.routers import dataset_router

app = FastAPI(
    title="Atlas Dataset Service",
    description="Manages dataset ingestion, validation, and publishing.",
    version="1.0.0",
)

app.include_router(dataset_router.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
