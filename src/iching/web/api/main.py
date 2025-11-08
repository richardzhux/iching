from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from iching.web.api.routes import router


def _allowed_origins() -> List[str]:
    raw = os.getenv("ICHING_ALLOWED_ORIGINS", "")
    if not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]


app = FastAPI(
    title="I Ching API",
    version="1.0.0",
    description="FastAPI service exposing the I Ching session engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"message": "I Ching API is running"}
