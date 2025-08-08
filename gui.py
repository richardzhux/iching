# app_gradio.py
# Modern Gradio web UI with digit-only manual lines, conditional manual input field,
# hidden 'q' backdoor, timestamped guilty/acquittal logs, auto-fill current time, and system (r) button.

import os
import io
import re
import json
import tempfile
from datetime import datetime
from typing import Optional, List, Tuple
from contextlib import redirect_stdout

import gradio as gr

# --- import your engine pieces ---
# Make sure bazicalc.py exports these:
#   compute_session_for_gui, HEX_FILE, GUACI_FOLDER, ACQUITTAL_DIR, COMPLETE_DIR
from bazicalc5 import compute_session_for_gui, HEX_FILE, GUACI_FOLDER, ACQUITTAL_DIR, COMPLETE_DIR
from sysusage import display_system_usage

# Try to import your closeai module (simplified version: no enforce_json/return_dict)
try:
    import closeai as ai_mod
    HAS_AI = True
except Exception:
    ai_mod = None
    HAS_AI = False


TOPICS = ["事业", "感情", "财运", "身体健康", "整体运势", "其他/跳过"]
METHODS = [
    ("五十蓍草法", "s"),
    ("三枚铜钱法", "c"),
    ("梅花易数法", "m"),
    ("手动输入",   "x"),
]
AI_MODELS = ["gpt-5-nano", "gpt-5", "o3"]


# ---------- helpers ----------

import threading, time, sys, os
# ... keep your other imports

def _schedule_shutdown_and_reply(reason: str):
    msg = f"会话已中止：{reason}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    acquit_path = _save_to_acquittal(msg)
    dl = _make_download_txt(msg)

    def _killer():
        time.sleep(1.0)
        try:
            demo.close()   # stop Gradio nicely
        except Exception:
            pass
        os._exit(0)        # hard-exit

    threading.Thread(target=_killer, daemon=True).start()

    return (msg + f"\n\n日志已保存：{acquit_path}\n即将退出…",
            "", {}, "", {}, dl)

def quit_now():
    return _schedule_shutdown_and_reply("用户点击了退出")

def _schedule_shutdown_and_reply(reason: str):
    """
    Save a short message to acquittal, return it to the UI, then shutdown server in ~1s.
    Returns tuple shaped like the normal outputs so UI can render a final message.
    """
    msg = f"会话已中止：{reason}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    acquit_path = _save_to_acquittal(msg)
    dl = _make_download_txt(msg)

    # Kill server after a short delay so UI can show the message
    def _killer():
        time.sleep(1.0)
        try:
            demo.close()   # politely stop Gradio (works in Gradio 4)
        except Exception:
            pass
        os._exit(0)        # hard-exit the Python process (reliable)

    threading.Thread(target=_killer, daemon=True).start()

    # Final UI payload
    return (msg + f"\n\n日志已保存：{acquit_path}\n即将退出…",
            "", {}, "", {}, dl)


def _expand_dir(p: str) -> str:
    return os.path.expanduser(p)

def _ensure_dir(d: str) -> None:
    os.makedirs(d, exist_ok=True)

def _timestamp() -> str:
    return datetime.now().strftime("%Y.%m.%d.%H%M")


def _save_to_acquittal(text: str) -> str:
    """Write a log to ACQUITTAL_DIR and return its path."""
    d = _expand_dir(ACQUITTAL_DIR)
    _ensure_dir(d)
    path = os.path.join(d, f"acquittal_{_timestamp()}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def _save_to_guilty(text: str) -> str:
    """Write a log to COMPLETE_DIR (guilty) and return its path."""
    d = _expand_dir(COMPLETE_DIR)
    _ensure_dir(d)
    path = os.path.join(d, f"guilty_{_timestamp()}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def _make_download_txt(content: str) -> str:
    """Create a temp .txt for the Gradio download component."""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
        f.write(content)
        return f.name

def _is_quit_token(s: Optional[str]) -> bool:
    return isinstance(s, str) and s.strip().lower() == "q"

def _method_key_from_label(label: str) -> str:
    return dict(METHODS)[label]

def _parse_manual_lines(s: str) -> Optional[List[int]]:
    """
    Accept either raw digits '898789' (preferred) or comma/Chinese-comma list.
    Returns list of 6 ints in {6,7,8,9}.
    """
    s = (s or "").strip()
    if not s:
        return None
    # digits-only like 898789
    if re.fullmatch(r"[6789]{6}", s):
        return [int(ch) for ch in s]
    # fallback: comma-separated like 8,9,8,7,8,9
    parts = [p.strip() for p in s.replace("，", ",").split(",") if p.strip()]
    try:
        vals = [int(x) for x in parts]
    except Exception:
        raise ValueError("六爻格式错误：请输入 6 位数字（如 898789），或用逗号分隔的 6 个值（如 8,9,8,7,8,9）")
    if len(vals) != 6 or any(v not in (6, 7, 8, 9) for v in vals):
        raise ValueError("六爻必须是 6 个值，且每个为 6/7/8/9（如 898789 或 8,9,8,7,8,9）")
    return vals

def _parse_datetime(s: str) -> datetime:
    s = s.strip()
    try:
        parts = s.split(".")
        if len(parts) != 4:
            raise ValueError
        year, month, day, hhmm = parts
        if len(hhmm) != 4 or not hhmm.isdigit():
            raise ValueError
        return datetime(int(year), int(month), int(day), int(hhmm[:2]), int(hhmm[2:]))
    except Exception:
        raise ValueError("时间格式错误：请用 yyyy.mm.dd.hhmm，例如 2025.08.08.1330")


def _abort_via_q(reason: str) -> Tuple[str, str, dict, str, dict, Optional[str]]:
    """
    Build an 'aborted' response + save to ACQUITTAL_DIR.
    Return tuple matching run_pipeline outputs:
      (summary_text, hex_text, najia_json, ai_text, session_json, download_file_path)
    """
    msg = f"会话已中止：{reason}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    acquit_path = _save_to_acquittal(msg)
    dl = _make_download_txt(msg)
    return (msg + f"\n\n日志已保存：{acquit_path}", "", {}, "", {}, dl)

def _capture_system_usage_text() -> str:
    """Capture stdout of display_system_usage() to a string."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        display_system_usage()
    return buf.getvalue().strip() or "(no output)"

def _run_ai_with_password(session_dict: dict, access_pw: str, model: str) -> str:
    """
    Run AI only if password matches env OPENAI_PW.
    Uses server's OPENAI_API_KEY; no key is taken from UI.
    """
    if not HAS_AI:
        return "（AI 模块未导入：未安装或文件不可见）"

    env_pw = os.environ.get("OPENAI_PW", "")
    if not access_pw:
        return "❌ 未提供访问密码。"
    if access_pw != env_pw:
        return "❌ 密码错误：请检查访问密码（与环境变量 OPENAI_PW 对比）。"

    # Avoid console prompts in GUI:
    ai_mod.ask_openai_password = lambda: True
    ai_mod.choose_model = lambda: model

    # Use system OPENAI_API_KEY; your closeai reads env if api_key=None
    return ai_mod.closeai(session_dict, api_key=None)


# ---------- main pipeline ----------

def run_pipeline(
    topic: str,
    user_question: str,
    method_label: str,
    manual_lines_text: str,
    use_now: bool,
    custom_dt: str,
    enable_ai: bool,
    access_pw: str,
    ai_model: str,
):
    # hidden 'q' backdoor: abort & acquittal if any single input is q
    if any([
        _is_quit_token(user_question),
        _is_quit_token(manual_lines_text),
        _is_quit_token(custom_dt),
        _is_quit_token(access_pw),
    ]):
        return _schedule_shutdown_and_reply("收到核弹密码，一枚Trident D5已从USS District of Columbia (SSBN-826)发射，祝好，再见。")

    try:
        m_key = _method_key_from_label(method_label)
        manual_lines = _parse_manual_lines(manual_lines_text) if m_key == "x" else None

        # time
        if use_now:
            dt_obj = None  # compute_session_for_gui will pull current time
        else:
            dt_obj = _parse_datetime(custom_dt)

        # Run core pipeline (no AI here so GUI won’t hang)
        session_dict, full_text = compute_session_for_gui(
            topic=topic,
            user_question=(user_question or None),
            method_key=m_key,
            use_current_time=use_now,
            custom_time=dt_obj,
            manual_lines=manual_lines,
            hex_file=HEX_FILE,
            guaci_folder=GUACI_FOLDER,
            enable_ai=False,
            api_key=None,
        )

        # AI (optional, password-gated)
        ai_text = ""
        if enable_ai:
            ai_text = _run_ai_with_password(session_dict, access_pw.strip(), ai_model)
            session_dict["ai_analysis"] = ai_text
            full_text = f"{full_text}\n\n【AI 分析】\n{ai_text}"

        # Save successful session to guilty with timestamp filename
        guilty_path = _save_to_guilty(full_text)

        # Summary panel
        summary_lines = [
            f"主题: {session_dict.get('topic') or '（未填）'}",
            f"问题: {session_dict.get('user_question') or '（无）'}",
            f"方法: {session_dict.get('method', '')}",
            f"时间: {session_dict.get('current_time_str', '')}",
            f"六爻: {session_dict.get('lines', [])}",
            f"已保存: {guilty_path}",
        ]
        summary_text = "\n".join(summary_lines)

        # Also prep a download .txt of the full output
        dl_path = _make_download_txt(full_text)

        return (
            summary_text,
            session_dict.get("hex_text", ""),
            session_dict.get("najia_data", {}) or {},
            ai_text,
            session_dict,
            dl_path
        )

    except Exception as e:
        # On error, save to acquittal and show link
        msg = f"错误：{e}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        acquit_path = _save_to_acquittal(msg)
        dl = _make_download_txt(msg)
        return (msg + f"\n\n错误日志已保存：{acquit_path}", "", {}, "", {}, dl)


def run_resources():
    try:
        usage = _capture_system_usage_text()
        msg = (
            "系统资源使用情况（r）：\n"
            f"{usage}\n\n"
            f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        # instead of returning a normal tuple, call the shutdown helper:
        return _schedule_shutdown_and_reply("系统资源查看后退出")
    except Exception as e:
        return _schedule_shutdown_and_reply(f"获取系统资源失败：{e}")



# ---------- UI ----------

with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
    css="""
    .gradio-container {font-family: Inter, ui-sans-serif, system-ui, -apple-system;}
    .header h1 {font-weight: 800; letter-spacing: 0.2px;}
    .subtle {opacity: 0.75}
    .footer {opacity: 0.6; font-size: 12px; margin-top: 8px}
    """
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
            user_question = gr.Textbox(label="具体问题（可空）", placeholder="例如：今年是否适合换工作？")

            method_label = gr.Radio([name for name, _ in METHODS], label="占卜方法", value=METHODS[0][0])

            # Manual lines textbox starts hidden; shown only when '手动输入' is selected
            manual_lines_text = gr.Textbox(
                label="手动输入六爻（自下而上；可直接输入 6 位数字如 898789）",
                placeholder="例如：898789 或 8,9,8,7,8,9",
                visible=False
            )

            with gr.Row():
                use_now = gr.Checkbox(True, label="使用当前时间")
                custom_dt = gr.Textbox(
                    label="自定义起卦时间（yyyy.mm.dd.hhmm）",
                    value=datetime.now().strftime("%Y.%m.%d.%H%M")
                )

            with gr.Accordion("OpenAI（可选；仅密码）", open=False):
                enable_ai = gr.Checkbox(False, label="启用 AI 分析")
                access_pw = gr.Textbox(label="访问密码（与环境变量 OPENAI_PW 匹配）", type="password")
                ai_model = gr.Dropdown(choices=AI_MODELS, value=AI_MODELS[0], label="模型")

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
                out_najia = gr.JSON(label="najia_data（结构化）")
            with gr.Tab("AI 分析"):
                out_ai = gr.Textbox(label="AI 输出", lines=16)
            with gr.Tab("会话字典（调试用）"):
                out_session = gr.JSON(label="session_dict")
            out_file = gr.File(label="下载结果（.txt）")

    # Show/hide manual lines when method changes
    def toggle_manual_visibility(method_label_val):
        visible = (method_label_val == "手动输入")
        return gr.update(visible=visible)
    method_label.change(toggle_manual_visibility, inputs=[method_label], outputs=[manual_lines_text])


    def toggle_time_field(use_now_val):
        if use_now_val:
            now_str = datetime.now().strftime("%Y.%m.%d.%H%M")
            return gr.update(value=now_str, interactive=False)
        else:
            return gr.update(interactive=True)
    use_now.change(toggle_time_field, inputs=[use_now], outputs=[custom_dt])


    # Main run
    run_btn.click(
        run_pipeline,
        inputs=[topic, user_question, method_label, manual_lines_text, use_now, custom_dt, enable_ai, access_pw, ai_model],
        outputs=[out_summary, out_hex, out_najia, out_ai, out_session, out_file],
        queue=True
    )
   
    quit_btn.click(
        quit_now,
        inputs=None,
        outputs=[out_summary, out_hex, out_najia, out_ai, out_session, out_file],
        queue=False
    )

    # System usage (r)
    r_btn.click(
        run_resources,
        inputs=None,
        outputs=[out_summary, out_hex, out_najia, out_ai, out_session, out_file],
        queue=False
    )

    gr.Markdown('<div class="footer">guaxiang: <code>{}</code> · guaci 目录: <code>{}</code></div>'.format(HEX_FILE, GUACI_FOLDER))



if __name__ == "__main__":
    # Auto-open browser
    demo.launch(inbrowser=True)
    # For server deploy:
    # demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=False)
