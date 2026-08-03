import os
#*from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#*from fastapi.staticfiles import StaticFiles

load_dotenv()

from backend.routes import analyze, export, rewrite  # noqa: E402

app = FastAPI(title="Resume-to-JD Alignment Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(rewrite.router)
app.include_router(export.router)

#*FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
#*app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
