from iching.config import build_app_config
from iching.services.session import SessionService


def test_session_service_manual_lines_without_ai():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        manual_lines=[7, 8, 7, 8, 7, 8],
        enable_ai=False,
        interactive=False,
    )

    assert result.topic == "事业"
    assert result.lines == [7, 8, 7, 8, 7, 8]
    assert "najia_data" in result.to_dict()
    assert result.ai_analysis is None
    assert "起卦时间" in result.full_text
