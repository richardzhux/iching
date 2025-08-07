import os
import sys
from openai import OpenAI

SYSTEM_PROMPT = (
    "请分析这个卦。请结合用神五行装配、世应神位置、内外卦动爻位置、"
    "起卦时间五行相克、爻辞、互卦错卦，以及每个卦引申出来的方位、动物、"
    "季节、人物性格、身体部位、自然意象等象征意义来分析。分析必须有理有据，不要胡编乱造。"
)

def closeai(file_path: str, api_key: str = None, topic: str = None, user_question: str = None) -> str:
    """
    Reads a hexagram explanation from file, adds topic and/or user question if given,
    and sends to OpenAI for analysis. Returns the response text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Please add it to your .env file or environment.")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Compose the full prompt
    full_prompt = ""
    if topic:
        full_prompt += f"本次占卜主题: {topic}\n"
    if user_question:
        full_prompt += f"具体问题: {user_question}\n"
    full_prompt += "\n卦辞解释如下：\n" + content

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",  # Use a valid model name
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ]
    )
    return response.choices[0].message.content.strip()