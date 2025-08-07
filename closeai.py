import os
import sys
from openai import OpenAI

SYSTEM_PROMPT = (
    "你是一个中国古代占卜大师。请分析这个卦。请结合用神五行装配、世应神位置、内外卦动爻位置、"
    "在卦象示意图中，哪一条爻的右侧有X或者O，哪一条爻就是动爻。"
    "本卦无动爻：取卦辞断。一爻动：取动爻之爻辞断。"
    "两爻动：一阴一阳时，取阴爻断（有“阳主过去，阴主未来”之说，兼顾时序），阳爻可参考为辅。同为阳或阴，取上动之爻断（即位置高的那个）。"
    "三爻动：取三爻中的中间一爻断（强调居中、平衡）。"
    "四爻动：取两静爻中的下爻断（即位置低的那个）。"
    "五爻动：以唯一静爻断。"
    "六爻全动：乾坤两卦用“用九”“用六”辞。其余六十二卦，取变卦之卦辞断。"
    "起卦时间五行相克、爻辞、互卦错卦，以及每个卦引申出来的方位、动物、"
    "季节、人物性格、身体部位、自然意象等象征意义来分析。分析必须有理有据，不要胡编乱造。"
)

def get_combined_explanation(primary_path, changed_path=None):
    explanation = ""
    if primary_path and os.path.exists(primary_path):
        with open(primary_path, "r", encoding="utf-8") as f:
            explanation += "【本卦内容】\n" + f.read().strip()
    if changed_path and changed_path != primary_path and os.path.exists(changed_path):
        explanation += "\n\n【变卦内容】\n"
        with open(changed_path, "r", encoding="utf-8") as f:
            explanation += f.read().strip()
    return explanation

def ask_openai_password():
    """循环要求输入OPENAI_PW，直至正确，最多3次"""
    pw = os.environ.get("OPENAI_PW")
    for _ in range(3):
        user_pw = input("\n请输入OPENAI API密码：").strip()
        if user_pw == pw:
            return True
        print("密码错误，请重新输入。")
    print("连续三次密码错误，程序退出。")
    sys.exit(1)

def choose_model():
    """
    交互式选择OpenAI模型（A/B/C/D 选项）。
    其它任何输入均默认为 gpt-4.1-nano，并给出提示。
    """
    models = [
        ("A", "gpt-4.1-nano", "最快 (推荐日常批量/工具/低成本)"),
        ("B", "gpt-4.1", "最均衡 (推荐复杂文本、推理)"),
        ("C", "o3", "最强/最慢 (复杂推理、大模型实验)")
    ]

    print("\n请选择OpenAI模型（默认：GPT-4.1-nano）：")
    for letter, m, desc in models:
        print(f"  [{letter}] {m.ljust(12)} —— {desc}")

    user_input = input("请尊贵的用户选择：").strip().upper()

    if user_input == "" or user_input == "A":
        return "gpt-4.1-nano"
    elif user_input == "B":
        return "gpt-4.1"
    elif user_input == "C":
        return "o3"
    else:
        print("警告：输入无效，已自动使用默认模型 gpt-4.1-nano。")
        return "gpt-4.1-nano"


def closeai(explanation: str, api_key: str = None, topic: str = None, user_question: str = None) -> str:

    ask_openai_password()

    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Please add it to your .env file or environment.")

    model = choose_model()
    
    full_prompt = ""
    if topic:
        full_prompt += f"本次占卜主题: {topic}\n"
    if user_question:
        full_prompt += f"具体问题: {user_question}\n"
    full_prompt += "\n卦辞解释如下：\n" + explanation

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4.1-nano",  # Use a valid model name
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ]
    )
    return response.choices[0].message.content.strip()