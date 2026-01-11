"""
Blauweiss Portal - Backend API
FastAPI + GitLab OAuth + PostgreSQL
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os

from .db.database import engine, Base, get_db
from .auth.oauth import router as auth_router
from .auth.jwt import get_current_user
from .routers import timesheets, invoices, users, health

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Blauweiss Portal API",
    description="Timesheet & Invoice Management for Blauweiss EDV",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - allow frontend origins
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://blauweiss.gitlab.io",
    "https://portal.blauweiss.at",
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(timesheets.router, prefix="/api/timesheets", tags=["Timesheets"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Invoices"])

@app.get("/")
async def root():
    return {
        "name": "Blauweiss Portal API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
