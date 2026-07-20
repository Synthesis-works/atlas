from fastapi import FastAPI
from .api.routers import reporting_router

app = FastAPI(
    title="Atlas Reporting Service",
    description="Read-only aggregation engine for Atlas Evaluation OS",
    version="1.0.0",
)

app.include_router(reporting_router.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
