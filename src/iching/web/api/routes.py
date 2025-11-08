from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from iching.web.models import ConfigResponse, SessionCreateRequest, SessionPayload
from iching.web.service import AccessDeniedError, SessionRunner, get_session_runner


router = APIRouter(prefix="/api", tags=["api"])


def _get_runner() -> SessionRunner:
    return get_session_runner()


@router.get("/health", tags=["meta"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigResponse)
def read_config(runner: SessionRunner = Depends(_get_runner)) -> ConfigResponse:
    return runner.config_response()


@router.post("/sessions", response_model=SessionPayload, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreateRequest,
    runner: SessionRunner = Depends(_get_runner),
) -> SessionPayload:
    try:
        return runner.run(request)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
