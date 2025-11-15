from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from iching.integrations.supabase_client import SupabaseAuthError
from iching.web.chat_service import ChatRateLimitError
from iching.web.models import (
    ChatTranscriptResponse,
    ChatTurnRequest,
    ChatTurnResponse,
    ConfigResponse,
    SessionCreateRequest,
    SessionPayload,
    SessionHistoryResponse,
)
from iching.web.service import (
    AccessDeniedError,
    RateLimitError,
    get_chat_service,
    SessionRunner,
    get_session_runner,
)


router = APIRouter(prefix="/api", tags=["api"])


def _get_runner() -> SessionRunner:
    return get_session_runner()


def _get_chat_service():
    return get_chat_service()


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
    authorization: str | None = Header(default=None, alias="Authorization"),
    runner: SessionRunner = Depends(_get_runner),
    chat_service=Depends(_get_chat_service),
) -> SessionPayload:
    client_ip = _extract_ip(http_request)
    supabase_user = None
    if authorization:
        token = _parse_bearer(authorization)
        try:
            supabase_user = chat_service.authenticate(token)
        except SupabaseAuthError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    try:
        return runner.run(request, client_ip=client_ip, user=supabase_user)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _parse_bearer(header_value: str | None) -> str:
    if not header_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录后才能继续追问。",
        )
    prefix = "bearer "
    normalized = header_value.strip()
    if not normalized.lower().startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="授权头无效。")
    token = normalized[len(prefix) :].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="授权头无效。")
    return token


@router.get(
    "/sessions/{session_id}/chat",
    response_model=ChatTranscriptResponse,
    status_code=status.HTTP_200_OK,
)
def read_chat_transcript(
    session_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    chat_service=Depends(_get_chat_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chat_service.authenticate(token)
        transcript = chat_service.fetch_transcript(session_id=session_id, user=user)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    messages = [
        {
            "id": item.get("id"),
            "role": item.get("role"),
            "content": item.get("content"),
            "tokens_in": item.get("tokens_in"),
            "tokens_out": item.get("tokens_out"),
            "created_at": item.get("created_at"),
        }
        for item in transcript["messages"]
    ]
    session_meta = transcript["session"]
    return ChatTranscriptResponse(
        session_id=session_id,
        summary_text=session_meta.get("summary_text"),
        initial_ai_text=session_meta.get("initial_ai_text"),
        payload_snapshot=session_meta.get("payload_snapshot"),
        followup_model=session_meta.get("followup_model"),
        messages=messages,
    )


@router.post(
    "/sessions/{session_id}/chat",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_message(
    session_id: str,
    payload: ChatTurnRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    chat_service=Depends(_get_chat_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chat_service.authenticate(token)
        result = chat_service.send_followup(
            session_id=session_id,
            user=user,
            message=payload.message,
            reasoning=payload.reasoning,
            verbosity=payload.verbosity,
            tone=payload.tone,
            model_override=payload.model,
        )
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ChatRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return ChatTurnResponse(
        session_id=session_id,
        assistant=result["assistant"],
        usage=result.get("usage", {}),
    )


@router.get("/sessions", response_model=SessionHistoryResponse)
def list_sessions(
    authorization: str | None = Header(default=None, alias="Authorization"),
    chat_service=Depends(_get_chat_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chat_service.authenticate(token)
        items = chat_service.list_sessions(user=user)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return SessionHistoryResponse(sessions=items)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    chat_service=Depends(_get_chat_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chat_service.authenticate(token)
        chat_service.delete_session(session_id=session_id, user=user)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
