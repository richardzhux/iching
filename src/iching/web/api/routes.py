from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from iching.web.models import ConfigResponse, SessionCreateRequest, SessionPayload
from iching.web.service import (
    AccessDeniedError,
    RateLimitError,
    SessionRunner,
    get_session_runner,
)


router = APIRouter(prefix="/api", tags=["api"])


def _get_runner() -> SessionRunner:
    return get_session_runner()


@router.get("/health", tags=["meta"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigResponse)
def read_config(runner: SessionRunner = Depends(_get_runner)) -> ConfigResponse:
    return runner.config_response()


def _extract_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/sessions", response_model=SessionPayload, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreateRequest,
    http_request: Request,
    runner: SessionRunner = Depends(_get_runner),
) -> SessionPayload:
    client_ip = _extract_ip(http_request)
    try:
        return runner.run(request, client_ip=client_ip)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
