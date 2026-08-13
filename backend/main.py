"""FastAPI entry point: `uvicorn backend.main:app --reload`."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import engagements, findings, items, reports, tools
from .ws import router as ws_router

app = FastAPI(title="surveil web", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engagements.router)
app.include_router(items.router)
app.include_router(findings.router)
app.include_router(tools.router)
app.include_router(reports.router)
app.include_router(ws_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
