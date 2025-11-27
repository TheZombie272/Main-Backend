from fastapi import FastAPI
from app.api.api_v1.api import api_router

app = FastAPI(title="Main-Backend")

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    # Lugar para inicializar conexiones a DB, caches, etc.
    pass


@app.on_event("shutdown")
async def shutdown_event():
    # Cerrar recursos si es necesario
    pass
