"""ui_testing_software service entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.login_mgmt.login_flow_backend.credential_validation.api import router as credential_validation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown


app = FastAPI(
    title="ui_testing_software",
    description="Backend service for UI testing — credential validation and beyond.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(credential_validation_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "ui_testing_software"}
