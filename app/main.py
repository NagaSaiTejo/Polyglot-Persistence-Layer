from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import init_postgres_db
from .ingest import process_event_file
from .reconcile import run_reconciliation
from .api import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB, run ingestion, run reconciliation
    print("Starting up: Initializing database...")
    init_postgres_db()
    
    print("Starting up: Processing events.log...")
    process_event_file()
    
    print("Starting up: Running reconciliation...")
    run_reconciliation()
    
    yield
    # Shutdown logic if any

app = FastAPI(lifespan=lifespan)

app.include_router(api_router)
