from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import sys

import streamlit as st

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from iching.config import build_app_config
from iching.integrations.ai import DEFAULT_MODEL, MODEL_CAPABILITIES
from iching.services.session import SessionService
from iching.web.models import SessionCreateRequest
from iching.web.service import AccessDeniedError, get_session_runner

CONFIG = build_app_config()
SERVICE = SessionService(config=CONFIG)
RUNNER = get_session_runner()

TOPICS = [value for key, value in SERVICE.TOPIC_MAP.items() if key != "q"]
METHODS = [(method.name, method.key) for method in SERVICE.methods.values()]
AI_MODELS = ["gpt-5.5", "gpt-5.4-mini", "gpt-5.3-codex", "gpt-4.1"]
AI_REASONING_LEVELS = [
    ("极简", "minimal"),
    ("低", "low"),
    ("中", "medium"),
    ("高", "high"),
]
AI_VERBOSITY_LEVELS = [
    ("简洁", "low"),
    ("适中", "medium"),
    ("详尽", "high"),
]

REASONING_LABEL_TO_VALUE = {label: value for label, value in AI_REASONING_LEVELS}
REASONING_VALUE_TO_LABEL = {value: label for label, value in AI_REASONING_LEVELS}
VERBOSITY_LABEL_TO_VALUE = {label: value for label, value in AI_VERBOSITY_LEVELS}
VERBOSITY_VALUE_TO_LABEL = {value: label for label, value in AI_VERBOSITY_LEVELS}


def _parse_manual_lines(raw: str) -> Optional[list[int]]:
    raw = (raw or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"[6789]{6}", raw):
        return [int(ch) for ch in raw]
    parts = [part.strip() for part in raw.replace("，", ",").split(",") if part.strip()]
    values = [int(part) for part in parts]
    if len(values) != 6 or any(value not in (6, 7, 8, 9) for value in values):
        raise ValueError("六爻必须是 6 个值，且每个为 6/7/8/9")
    return values


def _parse_datetime(raw: str) -> datetime:
    raw = raw.strip()
    parts = raw.split(".")
    if len(parts) != 4:
        raise ValueError("时间格式错误：请用 yyyy.mm.dd.hhmm")
    year, month, day, hhmm = parts
    if len(hhmm) != 4 or not hhmm.isdigit():
        raise ValueError("时间格式错误：请用 yyyy.mm.dd.hhmm")
    return datetime(int(year), int(month), int(day), int(hhmm[:2]), int(hhmm[2:]))


def _make_download(content: str) -> str:
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as handle:
        handle.write(content)
        return handle.name


def _run_session(
    topic: str,
    question: str,
    method_label: str,
    manual_lines_text: str,
    use_now: bool,
    custom_dt: str,
    enable_ai: bool,
    access_pw: str,
    ai_model: str,
    ai_reasoning_label: Optional[str],
    ai_verbosity_label: Optional[str],
) -> Tuple[str, str, str, str, dict, Optional[str]]:
    method_lookup = {name: key for name, key in METHODS}
    method_key = method_lookup[method_label]

    manual_lines = None
    if method_key == "x":
        manual_lines = _parse_manual_lines(manual_lines_text)
        if manual_lines is None:
            raise ValueError("手动输入模式需要提供六爻。")

    timestamp = None
    if not use_now:
        timestamp = _parse_datetime(custom_dt)

    capabilities = MODEL_CAPABILITIES.get(ai_model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    allowed_reasoning = capabilities.get("reasoning", [])
    default_reasoning = capabilities.get("default_reasoning")

    reasoning_value: Optional[str]
    if allowed_reasoning:
        requested_reasoning = REASONING_LABEL_TO_VALUE.get(ai_reasoning_label or "")
        if requested_reasoning in allowed_reasoning:
            reasoning_value = requested_reasoning
        else:
            reasoning_value = default_reasoning or allowed_reasoning[0]
    else:
        reasoning_value = None

    verbosity_value: Optional[str]
    if capabilities.get("verbosity"):
        default_verbosity = capabilities.get("default_verbosity", "medium")
        requested_verbosity = VERBOSITY_LABEL_TO_VALUE.get(ai_verbosity_label or "")
        if requested_verbosity in {"low", "medium", "high"}:
            verbosity_value = requested_verbosity
        else:
            verbosity_value = default_verbosity
    else:
        verbosity_value = None

    request = SessionCreateRequest(
        topic=topic,
        user_question=question or None,
        method_key=method_key,
        manual_lines=manual_lines,
        use_current_time=use_now,
        timestamp=timestamp,
        enable_ai=enable_ai,
        access_password=access_pw or None,
        ai_model=ai_model,
        ai_reasoning=reasoning_value,
        ai_verbosity=verbosity_value,
    )

    payload = RUNNER.run(request)
    download_path = _make_download(payload.full_text)

    return (
        payload.summary_text,
        payload.hex_text,
        payload.najia_text,
        payload.ai_text,
        payload.session_dict,
        download_path,
    )


def _reasoning_choices_for(model: str) -> list[str]:
    capabilities = MODEL_CAPABILITIES.get(model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    allowed = capabilities.get("reasoning", [])
    return [label for label, value in AI_REASONING_LEVELS if value in allowed]


def _default_reasoning_label(model: str) -> Optional[str]:
    choices = _reasoning_choices_for(model)
    if not choices:
        return None
    capabilities = MODEL_CAPABILITIES.get(model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    default_value = capabilities.get("default_reasoning") or next(
        (value for label, value in AI_REASONING_LEVELS if label in choices),
        None,
    )
    if default_value is None:
        return None
    return REASONING_VALUE_TO_LABEL.get(default_value)


def _default_verbosity_label(model: str) -> Optional[str]:
    capabilities = MODEL_CAPABILITIES.get(model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    if not capabilities.get("verbosity"):
        return None
    default_value = capabilities.get("default_verbosity", "medium")
    return VERBOSITY_VALUE_TO_LABEL.get(default_value, VERBOSITY_VALUE_TO_LABEL["medium"])


def update_ai_controls(
    selected_model: str,
    current_reasoning_label: Optional[str],
    current_verbosity_label: Optional[str],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    capabilities = MODEL_CAPABILITIES.get(selected_model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    allowed_reasoning = capabilities.get("reasoning", [])
    if allowed_reasoning:
        reasoning_choices = _reasoning_choices_for(selected_model)
        requested_value = REASONING_LABEL_TO_VALUE.get(current_reasoning_label or "")
        if requested_value not in allowed_reasoning:
            requested_value = capabilities.get("default_reasoning") or allowed_reasoning[0]
        reasoning_label = REASONING_VALUE_TO_LABEL.get(requested_value, reasoning_choices[0])
        reasoning_update = {
            "visible": True,
            "choices": reasoning_choices,
            "value": reasoning_label,
        }
    else:
        reasoning_update = {"visible": False, "choices": [], "value": None}

    if capabilities.get("verbosity"):
        default_verbosity = capabilities.get("default_verbosity", "medium")
        requested_verbosity = VERBOSITY_LABEL_TO_VALUE.get(current_verbosity_label or "")
        if requested_verbosity not in {"low", "medium", "high"}:
            requested_verbosity = default_verbosity
        verbosity_label = VERBOSITY_VALUE_TO_LABEL.get(requested_verbosity, VERBOSITY_VALUE_TO_LABEL["medium"])
        verbosity_update = {
            "visible": True,
            "choices": [label for label, _ in AI_VERBOSITY_LEVELS],
            "value": verbosity_label,
        }
    else:
        verbosity_update = {"visible": False, "choices": [], "value": None}

    return reasoning_update, verbosity_update


def _inject_streamlit_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --nw-purple: #4E2A84;
            --nw-purple-dark: #401F68;
            --text-dark: #1F2937;
        }
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(120% 160% at 0% 0%, rgba(255, 126, 185, 0.55), transparent),
                radial-gradient(140% 180% at 100% 0%, rgba(255, 182, 111, 0.45), transparent),
                radial-gradient(120% 160% at 0% 100%, rgba(152, 119, 255, 0.45), transparent),
                radial-gradient(140% 180% at 100% 100%, rgba(111, 210, 255, 0.25), transparent),
                #ffe2fc !important;
            color: #3a0f40;
            min-height: 100vh;
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            padding-top: 2.5rem;
            padding-bottom: 3.2rem;
            max-width: 920px;
        }
        .header h1 {
            font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            font-weight: 800;
            letter-spacing: 0.2px;
            color: #430d4d;
        }
        .header .subtle {
            opacity: 0.78;
            color: #5a1c64;
            font-size: 0.95rem;
        }
        .glass-panel {
            background: rgba(255, 255, 255, 0.35);
            border-radius: 20px;
            padding: 24px 26px;
            border: 1px solid rgba(255, 255, 255, 0.55);
            box-shadow: 0 28px 64px -36px rgba(78, 42, 132, 0.35);
            backdrop-filter: blur(26px);
            -webkit-backdrop-filter: blur(26px);
            color: var(--text-dark);
            margin-bottom: 22px;
        }
        .glass-panel div[data-testid="column"] {
            padding: 6px 8px;
        }
        .badge-label {
            display: inline-flex;
            align-items: center;
            background: rgba(78, 42, 132, 0.82);
            color: #F9FAFB;
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 999px;
            padding: 6px 18px;
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.3px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            margin-bottom: 10px;
            transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .badge-label:hover {
            background: rgba(64, 31, 104, 0.9);
            border-color: rgba(255, 255, 255, 0.65);
            box-shadow: 0 10px 24px -16px rgba(64, 31, 104, 0.45);
        }
        div[data-testid="stTextInput"] label,
        div[data-testid="stTextArea"] label,
        div[data-testid="stSelectbox"] label,
        div[data-testid="stRadio"] label,
        div[data-testid="stCheckbox"] label,
        div[data-testid="stNumberInput"] label {
            font-weight: 600;
            color: var(--text-dark);
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stSelectbox"] div[role="combobox"],
        div[data-testid="stNumberInput"] input {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(78, 42, 132, 0.25);
            color: var(--text-dark);
            border-radius: 12px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
            caret-color: var(--nw-purple);
        }
        div[data-testid="stTextInput"] input::placeholder,
        div[data-testid="stTextArea"] textarea::placeholder {
            color: rgba(55, 65, 81, 0.62);
        }
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stSelectbox"] div[role="combobox"]:focus,
        div[data-testid="stSelectbox"] div[role="combobox"]:focus-within {
            outline: none;
            box-shadow: 0 0 0 3px rgba(78, 42, 132, 0.35);
            border-color: rgba(78, 42, 132, 0.55);
            background: rgba(255, 255, 255, 0.98);
        }
        div[data-testid="stSelectbox"] div[role="listbox"] {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(78, 42, 132, 0.25);
            backdrop-filter: blur(18px);
        }
        div[data-testid="stSelectbox"] div[role="option"] {
            color: var(--text-dark);
        }
        div[data-testid="stSelectbox"] div[role="option"]:hover {
            background: rgba(78, 42, 132, 0.1);
        }
        div[data-testid="stCheckbox"] input {
            accent-color: var(--nw-purple);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        div[data-testid="stRadio"] div[role="radio"] {
            background: rgba(78, 42, 132, 0.78);
            border: 1px solid rgba(255, 255, 255, 0.45);
            border-radius: 14px;
            padding: 6px 18px;
            color: #F9FAFB;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stRadio"] div[role="radio"]:hover {
            background: rgba(64, 31, 104, 0.85);
            border-color: rgba(255, 255, 255, 0.6);
            box-shadow: 0 10px 24px -18px rgba(64, 31, 104, 0.45);
        }
        div[data-testid="stRadio"] div[role="radio"][aria-checked="true"] {
            background: rgba(64, 31, 104, 0.9);
            border-color: rgba(255, 255, 255, 0.7);
            font-weight: 700;
        }
        .stButton > button {
            width: 100%;
            border-radius: 999px;
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.75);
            color: #2D0D56;
            font-weight: 700;
            box-shadow: 0 18px 44px -30px rgba(78, 42, 132, 0.4);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            text-shadow: 0 1px 10px rgba(255, 255, 255, 0.55);
            transition: background 0.2s ease, box-shadow 0.2s ease, color 0.2s ease;
        }
        .stButton > button:hover {
            background: rgba(255, 255, 255, 0.12);
            box-shadow: 0 22px 54px -30px rgba(64, 31, 104, 0.5);
            color: #23094B;
        }
        .output-section {
            background: rgba(255, 247, 252, 0.65);
            padding: 20px 24px 18px;
            border-radius: 18px;
            border: 1px solid rgba(255, 189, 249, 0.6);
            box-shadow: 0 28px 52px -30px rgba(200, 70, 200, 0.45);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            margin-bottom: 22px;
        }
        .output-section h2 {
            margin-bottom: 12px;
            color: #3d0f45;
            font-weight: 700;
        }
        .output-section pre {
            background: rgba(255, 255, 255, 0.6);
            border: 1px solid rgba(255, 189, 249, 0.5);
            color: #321042;
            border-radius: 12px;
            padding: 14px;
            white-space: pre-wrap;
        }
        .footer {
            opacity: 0.7;
            font-size: 12px;
            margin-top: 18px;
            color: #5e2468;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _badge(label: str) -> None:
    st.markdown(f'<div class="badge-label">{label}</div>', unsafe_allow_html=True)


def _render_text_area(label: str, value: str, key: str, height: int = 220) -> None:
    st.text_area(label, value=value, key=key, height=height, label_visibility="collapsed")


def _render_output_section(title: str, body: str, key: str, height: int = 220) -> None:
    if not body:
        return
    st.markdown(f'<div class="output-section"><h2>{title}</h2>', unsafe_allow_html=True)
    _render_text_area("", body, key=key, height=height)
    st.markdown("</div>", unsafe_allow_html=True)


def _init_session_state() -> None:
    defaults = {
        "topic": TOPICS[0],
        "user_question": "",
        "method": METHODS[0][0],
        "manual_lines": "",
        "use_now": True,
        "custom_dt": datetime.now().strftime("%Y.%m.%d.%H%M"),
        "enable_ai": False,
        "access_pw": "",
        "ai_model": DEFAULT_MODEL,
        "ai_reasoning": _default_reasoning_label(DEFAULT_MODEL),
        "ai_verbosity": _default_verbosity_label(DEFAULT_MODEL),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("run_error", "")
    st.session_state.setdefault("summary_text", "")
    st.session_state.setdefault("hex_text", "")
    st.session_state.setdefault("najia_text", "")
    st.session_state.setdefault("ai_text", "")
    st.session_state.setdefault("session_json", {})
    st.session_state.setdefault("download_path", None)


def _handle_run_button(
    topic: str,
    question: str,
    method_label: str,
    manual_lines_text: str,
    use_now: bool,
    custom_dt: str,
    enable_ai: bool,
    access_pw: str,
    ai_model: str,
    ai_reasoning_label: Optional[str],
    ai_verbosity_label: Optional[str],
) -> None:
    try:
        (
            summary,
            hex_text,
            najia_text,
            ai_text,
            session_dict,
            download_path,
        ) = _run_session(
            topic,
            question,
            method_label,
            manual_lines_text,
            use_now,
            custom_dt,
            enable_ai,
            access_pw,
            ai_model,
            ai_reasoning_label,
            ai_verbosity_label,
        )
        st.session_state.update(
            {
                "summary_text": summary,
                "hex_text": hex_text,
                "najia_text": najia_text,
                "ai_text": ai_text,
                "session_json": session_dict,
                "download_path": download_path,
                "run_error": "",
            }
        )
    except AccessDeniedError as exc:
        st.session_state.update(
            {
                "run_error": str(exc),
                "summary_text": "",
                "hex_text": "",
                "najia_text": "",
                "ai_text": "",
                "session_json": {},
                "download_path": None,
            }
        )
    except Exception as exc:  # noqa: BLE001
        st.session_state.update(
            {
                "run_error": str(exc),
                "summary_text": "",
                "hex_text": "",
                "najia_text": "",
                "ai_text": "",
                "session_json": {},
                "download_path": None,
            }
        )


def main() -> None:
    st.set_page_config(page_title="I Ching — Web", page_icon="🔮", layout="wide")
    _inject_streamlit_css()
    _init_session_state()

    st.markdown(
        """
        <div class="header">
          <h1>🔮 I Ching — Web</h1>
          <div class="subtle">现代化界面 · 手动/随机起卦 · 可选 AI 分析 · 自动归档</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 2], gap="medium")
        with col1:
            _badge("占卜主题")
            st.selectbox("", TOPICS, index=TOPICS.index(st.session_state.topic), key="topic", label_visibility="collapsed")
        with col2:
            _badge("具体问题（可空）")
            st.text_input("", key="user_question", placeholder="例如：今年是否适合换工作？", label_visibility="collapsed")

        col_left, col_right = st.columns(2, gap="medium")
        with col_left:
            _badge("占卜方法")
            method_choices = [label for label, _ in METHODS]
            default_index = method_choices.index(st.session_state.method)
            st.radio("", method_choices, index=default_index, key="method", label_visibility="collapsed")
            if st.session_state.method == "手动输入":
                _badge("手动输入六爻（自下而上；可直接输入 6 位数字如 898789）")
                st.text_input("", key="manual_lines", placeholder="例如：898789 或 8,9,8,7,8,9", label_visibility="collapsed")

        with col_right:
            _badge("时间设置")
            use_now_value = st.checkbox("使用当前时间", value=st.session_state.use_now, key="use_now")
            if use_now_value:
                st.session_state.custom_dt = datetime.now().strftime("%Y.%m.%d.%H%M")
            _badge("自定义起卦时间（yyyy.mm.dd.hhmm）")
            st.text_input(
                "",
                key="custom_dt",
                value=st.session_state.custom_dt,
                label_visibility="collapsed",
                disabled=use_now_value,
            )

        col_a, col_b, col_c = st.columns([1, 1, 1], gap="medium")
        with col_a:
            _badge("启用 AI 分析")
            st.checkbox("启用", value=st.session_state.enable_ai, key="enable_ai")
            _badge("访问密码")
            st.text_input("", key="access_pw", type="password", label_visibility="collapsed", placeholder="输入访问密码")

        with col_b:
            _badge("模型")
            st.selectbox("", AI_MODELS, index=AI_MODELS.index(st.session_state.ai_model), key="ai_model", label_visibility="collapsed")

            reasoning_config, verbosity_config = update_ai_controls(
                st.session_state.ai_model,
                st.session_state.get("ai_reasoning"),
                st.session_state.get("ai_verbosity"),
            )

            if reasoning_config["visible"]:
                _badge("推理力度")
                target_value = reasoning_config["value"] or reasoning_config["choices"][0]
                if st.session_state.get("ai_reasoning") not in reasoning_config["choices"]:
                    st.session_state.ai_reasoning = target_value
                st.radio(
                    "",
                    reasoning_config["choices"],
                    index=reasoning_config["choices"].index(st.session_state.ai_reasoning),
                    key="ai_reasoning",
                    label_visibility="collapsed",
                )
            else:
                st.session_state.ai_reasoning = None

        with col_c:
            if verbosity_config["visible"]:
                _badge("输出篇幅")
                target_value = verbosity_config["value"] or verbosity_config["choices"][0]
                if st.session_state.get("ai_verbosity") not in verbosity_config["choices"]:
                    st.session_state.ai_verbosity = target_value
                st.radio(
                    "",
                    verbosity_config["choices"],
                    index=verbosity_config["choices"].index(st.session_state.ai_verbosity),
                    key="ai_verbosity",
                    label_visibility="collapsed",
                )
                st.caption("仅 GPT-5 系列支持：控制回答的简洁程度与篇幅。")
            else:
                st.session_state.ai_verbosity = None
                st.caption("当前模型不支持调整输出篇幅。")

        run_clicked = st.button("▶️ 开始起卦", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    if run_clicked:
        _handle_run_button(
            st.session_state.topic,
            st.session_state.user_question,
            st.session_state.method,
            st.session_state.manual_lines,
            st.session_state.use_now,
            st.session_state.custom_dt,
            st.session_state.enable_ai,
            st.session_state.access_pw,
            st.session_state.ai_model,
            st.session_state.ai_reasoning,
            st.session_state.ai_verbosity,
        )

    if st.session_state.run_error:
        st.error(st.session_state.run_error)

    _render_output_section("概要", st.session_state.summary_text, key="summary_output", height=240)
    _render_output_section("卦辞与解释", st.session_state.hex_text, key="hex_output", height=360)
    _render_output_section("纳甲数据", st.session_state.najia_text, key="najia_output", height=280)
    _render_output_section("AI 分析", st.session_state.ai_text, key="ai_output", height=280)

    if st.session_state.session_json:
        st.markdown('<div class="output-section"><h2>会话字典（调试用）</h2>', unsafe_allow_html=True)
        st.json(st.session_state.session_json)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.download_path:
        try:
            with open(st.session_state.download_path, "rb") as handle:
                file_bytes = handle.read()
            st.download_button(
                "下载结果（.txt）",
                data=file_bytes,
                file_name="iching_session.txt",
                mime="text/plain",
            )
        except FileNotFoundError:
            st.warning("找不到下载文件，请重新生成。")

def launch(*, inbrowser: bool = True) -> None:
    """Launch the Streamlit app as a subprocess for compatibility with previous API."""
    script_path = Path(__file__).resolve()
    command = ["streamlit", "run", str(script_path)]
    env = os.environ.copy()
    if not inbrowser:
        env["STREAMLIT_SERVER_HEADLESS"] = "true"
    try:
        import subprocess

        subprocess.run(command, check=True, env=env)
    except FileNotFoundError as exc:  # noqa: PERF203
        raise RuntimeError("未找到 streamlit 命令，请先安装 streamlit。") from exc


if __name__ == "__main__":
    main()
