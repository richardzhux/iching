from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from iching.integrations.supabase_client import SupabaseAuthError
from iching.core.metaphysics import build_metaphysics_chart
from iching.web.chat_service import ChatRateLimitError
from iching.web.chart_service import ChartArchiveService
from iching.web.models import (
    MetaphysicsChartListResponse,
    MetaphysicsChartRecord,
    ChatTranscriptResponse,
    ChatTurnRequest,
    ChatTurnResponse,
    ConfigResponse,
    MetaphysicsChartRequest,
    MetaphysicsChartResponse,
    MetaphysicsChartSaveRequest,
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
logger = logging.getLogger(__name__)


def _get_runner() -> SessionRunner:
    return get_session_runner()


def _get_chat_service():
    return get_chat_service()


def _get_chart_service() -> ChartArchiveService:
    return ChartArchiveService(get_chat_service().client)


@router.get("/health", tags=["meta"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigResponse)
def read_config(runner: SessionRunner = Depends(_get_runner)) -> ConfigResponse:
    return runner.config_response()


@router.post("/tools/metaphysics", response_model=MetaphysicsChartResponse)
def calculate_metaphysics_chart(payload: MetaphysicsChartRequest) -> MetaphysicsChartResponse:
    try:
        result = build_metaphysics_chart(
            payload.timestamp,
            timezone_name=payload.timezone,
            longitude=payload.longitude,
            use_true_solar_time=payload.use_true_solar_time,
            day_boundary=payload.day_boundary,
            calendar_type=payload.calendar_type,
            is_leap_month=payload.is_leap_month,
            gender=payload.gender,
            birth_place=payload.birth_place,
            hour_uncertain=payload.hour_uncertain,
            dayun_algorithm=payload.dayun_algorithm,
            lunar_year=payload.lunar_year,
            lunar_month=payload.lunar_month,
            lunar_day=payload.lunar_day,
            lunar_hour=payload.lunar_hour,
            lunar_minute=payload.lunar_minute,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MetaphysicsChartResponse(**result)


@router.post(
    "/metaphysics/charts",
    response_model=MetaphysicsChartRecord,
    status_code=status.HTTP_201_CREATED,
)
def save_metaphysics_chart(
    payload: MetaphysicsChartSaveRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    chart_service: ChartArchiveService = Depends(_get_chart_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chart_service.authenticate(token)
        return chart_service.save_chart(request=payload, user=user)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="命盘暂时无法保存，请稍后重试。") from exc


@router.get("/metaphysics/charts", response_model=MetaphysicsChartListResponse)
def list_metaphysics_charts(
    authorization: str | None = Header(default=None, alias="Authorization"),
    chart_service: ChartArchiveService = Depends(_get_chart_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chart_service.authenticate(token)
        return {"charts": chart_service.list_charts(user=user)}
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="命盘档案暂时无法读取。") from exc


@router.get("/metaphysics/charts/{chart_id}", response_model=MetaphysicsChartRecord)
def read_metaphysics_chart(
    chart_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    chart_service: ChartArchiveService = Depends(_get_chart_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chart_service.authenticate(token)
        return chart_service.fetch_chart(chart_id=chart_id, user=user)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="命盘暂时无法读取。") from exc


@router.delete("/metaphysics/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_metaphysics_chart(
    chart_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    chart_service: ChartArchiveService = Depends(_get_chart_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chart_service.authenticate(token)
        chart_service.delete_chart(chart_id=chart_id, user=user)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="命盘暂时无法删除。") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
            "model": item.get("model"),
            "reasoning": item.get("reasoning"),
            "verbosity": item.get("verbosity"),
            "tone": item.get("tone"),
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
        ai_reasoning=session_meta.get("ai_reasoning"),
        ai_verbosity=session_meta.get("ai_verbosity"),
        ai_tone=session_meta.get("ai_tone"),
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
            restart=payload.restart,
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


@router.post(
    "/sessions/{session_id}/chat/stream",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
)
def stream_chat_message(
    session_id: str,
    payload: ChatTurnRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    chat_service=Depends(_get_chat_service),
):
    token = _parse_bearer(authorization)
    try:
        user = chat_service.authenticate(token)
        events = chat_service.stream_followup(
            session_id=session_id,
            user=user,
            message=payload.message,
            reasoning=payload.reasoning,
            verbosity=payload.verbosity,
            tone=payload.tone,
            model_override=payload.model,
            restart=payload.restart,
        )
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ChatRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    def event_source():
        try:
            for item in events:
                event_type = str(item.get("type") or "message")
                payload_data = {key: value for key, value in item.items() if key != "type"}
                yield f"event: {event_type}\ndata: {json.dumps(payload_data, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Streaming chat failed", extra={"session_id": session_id})
            yield f"event: error\ndata: {json.dumps({'detail': 'AI 流式响应失败，请重试。'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
