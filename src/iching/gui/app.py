from __future__ import annotations

import io
import os
import re
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

import gradio as gr

from iching.config import PATHS, build_app_config
from iching.core.system import display_system_usage
from iching.integrations.ai import DEFAULT_MODEL, MODEL_CAPABILITIES
from iching.services.session import SessionResult, SessionService

CONFIG = build_app_config()
SERVICE = SessionService(config=CONFIG)

TOPICS = [value for key, value in SERVICE.TOPIC_MAP.items() if key != "q"]
METHODS = [(method.name, method.key) for method in SERVICE.methods.values()]
AI_MODELS = ["gpt-5-nano", "gpt-4.1-nano", "gpt-5", "o3"]
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


def _capture_system_usage() -> str:
    buffer = io.StringIO()
    buffer.write(display_system_usage())
    return buffer.getvalue()


def _ensure_dir(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _save_archive(directory: Path, prefix: str, content: str) -> Path:
    directory = _ensure_dir(directory)
    timestamp = datetime.now().strftime("%Y.%m.%d.%H%M%S")
    path = directory / f"{prefix}_{timestamp}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def _make_download(content: str) -> str:
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as handle:
        handle.write(content)
        return handle.name


def _validate_ai_password(password: str) -> Tuple[bool, str]:
    expected = os.getenv("OPENAI_PW", "")
    if not expected:
        return False, "❌ 环境变量 OPENAI_PW 未设置。"
    if not password:
        return False, "❌ 未提供访问密码。"
    if password != expected:
        return False, "❌ 密码错误：请检查访问密码（与环境变量 OPENAI_PW 对比）。"
    return True, ""


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

    ai_allowed = False
    if enable_ai:
        ai_allowed, message = _validate_ai_password(access_pw)
        if not ai_allowed:
            return (
                message,
                "",
                "",
                "",
                {},
                _make_download(message),
            )

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

    result = SERVICE.create_session(
        topic=topic,
        user_question=(question or None),
        method_key=method_key,
        use_current_time=use_now,
        timestamp=timestamp,
        manual_lines=manual_lines,
        enable_ai=ai_allowed,
        ai_model=ai_model,
        ai_reasoning=reasoning_value,
        ai_verbosity=verbosity_value,
        interactive=False,
    )

    archive_path = _save_archive(CONFIG.paths.archive_complete_dir, "guilty", result.full_text)

    summary = [
        f"主题: {result.topic or '（未填）'}",
        f"问题: {result.user_question or '（无）'}",
        f"方法: {result.method}",
        f"时间: {result.current_time_str}",
        f"六爻: {result.lines}",
        f"已保存: {archive_path}",
    ]

    session_dict = result.to_dict()
    session_dict["ai_analysis"] = result.ai_analysis

    download_path = _make_download(result.full_text)

    return (
        "\n".join(summary),
        result.hex_text,
        result.najia_text,
        result.ai_analysis or "",
        session_dict,
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


def _verbosity_visible(model: str) -> bool:
    capabilities = MODEL_CAPABILITIES.get(model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    return bool(capabilities.get("verbosity"))


def update_ai_controls(
    selected_model: str,
    current_reasoning_label: Optional[str],
    current_verbosity_label: Optional[str],
) -> Tuple[Any, Any]:
    capabilities = MODEL_CAPABILITIES.get(selected_model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    allowed_reasoning = capabilities.get("reasoning", [])
    if allowed_reasoning:
        reasoning_choices = _reasoning_choices_for(selected_model)
        requested_value = REASONING_LABEL_TO_VALUE.get(current_reasoning_label or "")
        if requested_value not in allowed_reasoning:
            requested_value = capabilities.get("default_reasoning") or allowed_reasoning[0]
        reasoning_label = REASONING_VALUE_TO_LABEL.get(requested_value, reasoning_choices[0])
        reasoning_update = gr.update(
            visible=True,
            choices=reasoning_choices,
            value=reasoning_label,
        )
    else:
        reasoning_update = gr.update(visible=False, choices=[], value=None)

    if capabilities.get("verbosity"):
        default_verbosity = capabilities.get("default_verbosity", "medium")
        requested_verbosity = VERBOSITY_LABEL_TO_VALUE.get(current_verbosity_label or "")
        if requested_verbosity not in {"low", "medium", "high"}:
            requested_verbosity = default_verbosity
        verbosity_label = VERBOSITY_VALUE_TO_LABEL.get(requested_verbosity, VERBOSITY_VALUE_TO_LABEL["medium"])
        verbosity_update = gr.update(
            visible=True,
            choices=[label for label, _ in AI_VERBOSITY_LEVELS],
            value=verbosity_label,
        )
    else:
        verbosity_update = gr.update(visible=False, choices=[], value=None)

    return reasoning_update, verbosity_update


def _abort_with_message(reason: str) -> Tuple[str, str, str, str, dict, Optional[str]]:
    msg = f"会话已中止：{reason}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    archive_path = _save_archive(CONFIG.paths.archive_acquittal_dir, "acquittal", msg)
    download_path = _make_download(msg)
    return (msg + f"\n\n日志已保存：{archive_path}", "", "", "", {}, download_path)


def _shutdown_after_delay() -> None:
    time.sleep(1.0)
    try:
        demo.close()
    except Exception:
        pass
    os._exit(0)


def run_resources() -> Tuple[str, str, str, str, dict, Optional[str]]:
    try:
        usage = _capture_system_usage()
        msg = (
            "系统资源使用情况：\n"
            f"{usage}\n\n"
            f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        threading.Thread(target=_shutdown_after_delay, daemon=True).start()
        return _abort_with_message("系统资源查看后退出")
    except Exception as exc:
        return _abort_with_message(f"获取系统资源失败：{exc}")


def quit_now() -> Tuple[str, str, str, str, dict, Optional[str]]:
    threading.Thread(target=_shutdown_after_delay, daemon=True).start()
    return _abort_with_message("用户点击了退出")


with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
    css="""
    .gradio-container {font-family: Inter, ui-sans-serif, system-ui, -apple-system;}
    .header h1 {font-weight: 800; letter-spacing: 0.2px;}
    .subtle {opacity: 0.75}
    .footer {opacity: 0.6; font-size: 12px; margin-top: 8px}
    """,
) as demo:
    gr.Markdown(
        """
        <div class="header">
          <h1>🔮 I Ching — Web</h1>
          <div class="subtle">现代化界面 · 手动/随机起卦 · 可选 AI 分析 · 自动归档</div>
        </div>
        """,
    )

    with gr.Row():
        with gr.Column(scale=3, min_width=360):
            topic = gr.Dropdown(TOPICS, label="占卜主题", value=TOPICS[0])
            user_question = gr.Textbox(
                label="具体问题（可空）", placeholder="例如：今年是否适合换工作？"
            )

            method_label = gr.Radio(
                [label for label, _ in METHODS],
                label="占卜方法",
                value=METHODS[0][0],
            )

            manual_lines_text = gr.Textbox(
                label="手动输入六爻（自下而上；可直接输入 6 位数字如 898789）",
                placeholder="例如：898789 或 8,9,8,7,8,9",
                visible=False,
            )

            with gr.Row():
                use_now = gr.Checkbox(True, label="使用当前时间")
                custom_dt = gr.Textbox(
                    label="自定义起卦时间（yyyy.mm.dd.hhmm）",
                    value=datetime.now().strftime("%Y.%m.%d.%H%M"),
                )

            with gr.Accordion("OpenAI（可选；仅密码）", open=False):
                enable_ai = gr.Checkbox(False, label="启用 AI 分析")
                access_pw = gr.Textbox(
                    label="访问密码（与环境变量 OPENAI_PW 匹配）", type="password"
                )
                ai_model = gr.Dropdown(
                    choices=AI_MODELS,
                    value=DEFAULT_MODEL,
                    label="模型",
                )
                ai_reasoning = gr.Radio(
                    choices=_reasoning_choices_for(DEFAULT_MODEL),
                    value=_default_reasoning_label(DEFAULT_MODEL),
                    label="推理力度",
                    info="极简=最快；力度越高越慢但推理更充分",
                    visible=bool(_reasoning_choices_for(DEFAULT_MODEL)),
                )
                ai_verbosity = gr.Radio(
                    choices=[label for label, _ in AI_VERBOSITY_LEVELS],
                    value=_default_verbosity_label(DEFAULT_MODEL),
                    label="输出篇幅",
                    info="仅 GPT-5 系列支持：控制回答的简洁程度与篇幅。",
                    visible=_verbosity_visible(DEFAULT_MODEL),
                )

            with gr.Row():
                run_btn = gr.Button("▶️ 开始起卦", variant="primary")
                r_btn = gr.Button("🖥️ 系统资源 (r)", variant="secondary")
                quit_btn = gr.Button("⛔ 退出 (q)", variant="stop")

        with gr.Column(scale=5):
            with gr.Tab("概览"):
                out_summary = gr.Textbox(label="概要", lines=8)
            with gr.Tab("卦辞与解释"):
                out_hex = gr.Textbox(label="全文", lines=18)
            with gr.Tab("纳甲数据"):
                out_najia = gr.Textbox(label="纳甲排盘", lines=12)
            with gr.Tab("AI 分析"):
                out_ai = gr.Textbox(label="AI 输出", lines=16)
            with gr.Tab("会话字典（调试用）"):
                out_session = gr.JSON(label="session_dict")
            out_file = gr.File(label="下载结果（.txt）")

    def toggle_manual_visibility(selected_method: str):
        return gr.update(visible=(selected_method == "手动输入"))

    method_label.change(
        toggle_manual_visibility,
        inputs=[method_label],
        outputs=[manual_lines_text],
    )

    def toggle_time_field(checked: bool):
        if checked:
            now_str = datetime.now().strftime("%Y.%m.%d.%H%M")
            return gr.update(value=now_str, interactive=False)
        return gr.update(interactive=True)

    use_now.change(toggle_time_field, inputs=[use_now], outputs=[custom_dt])

    ai_model.change(
        update_ai_controls,
        inputs=[ai_model, ai_reasoning, ai_verbosity],
        outputs=[ai_reasoning, ai_verbosity],
    )

    run_btn.click(
        _run_session,
        inputs=[
            topic,
            user_question,
            method_label,
            manual_lines_text,
            use_now,
            custom_dt,
            enable_ai,
            access_pw,
            ai_model,
            ai_reasoning,
            ai_verbosity,
        ],
        outputs=[out_summary, out_hex, out_najia, out_ai, out_session, out_file],
        queue=True,
    )

    quit_btn.click(
        quit_now,
        inputs=None,
        outputs=[out_summary, out_hex, out_najia, out_ai, out_session, out_file],
        queue=False,
    )

    r_btn.click(
        run_resources,
        inputs=None,
        outputs=[out_summary, out_hex, out_najia, out_ai, out_session, out_file],
        queue=False,
    )

    gr.Markdown(
        f'<div class="footer">数据目录: <code>{PATHS.data_dir}</code> · guaci 目录: <code>{PATHS.guaci_dir}</code></div>'
    )


def launch(*, inbrowser: bool = True) -> None:
    demo.launch(inbrowser=inbrowser)


if __name__ == "__main__":
    launch()
