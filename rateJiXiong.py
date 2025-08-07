sorted_terms_with_scores = {
    "元吉": 100,
    "大吉": 98,
    "元亨": 95,
    "吉": 90,
    "终吉": 80,
    "征吉": 77,
    "贞吉": 74,
    "夙吉": 72,
    "利贞": 70,
    "利见大人": 70,
    "利涉大川": 65,
    "无不利": 60,
    "无悔": 55,
    "无攸利": 52,
    "悔亡": 50,
    "无咎": 40,
    "有悔": 35,
    "吝": 30,
    "贞吝": 25,
    "终吝": 25,
    "厉": 20,
    "贞厉": 15,
    "咎": 5,
    "凶": 0,
    "贞凶": 0,
}


from statistics import mean, median


def analyze_text(text: str) -> str:
    """Return a formatted analysis of auspicious keywords in the given text."""

    # Work on a copy so we can remove matched keywords and avoid double counting
    remaining = text
    found: dict[str, int] = {}

    # Sort keywords by length so longer phrases are matched first
    for term in sorted(sorted_terms_with_scores.keys(), key=len, reverse=True):
        count = remaining.count(term)
        if count:
            found[term] = count
            remaining = remaining.replace(term, " " * len(term))

    scores: list[int] = []
    for term, cnt in found.items():
        scores.extend([sorted_terms_with_scores[term]] * cnt)

    lines = ["Found"]
    for term, cnt in found.items():
        lines.append(f"{term} x{cnt}")

    if scores:
        lines.append(f"Average Score: {mean(scores):.2f}")
        lines.append(f"Median Score: {median(scores):.2f}")
    else:
        lines.append("Average Score: N/A")
        lines.append("Median Score: N/A")

    return "\n".join(lines)


def analyze_file(file_path: str) -> str:
    """Load a file and analyze its contents for auspicious keywords."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return analyze_text(content)


"""
不利有攸往，一个字只能算在一个词里
不能同时识别成利有攸往

统计没有关键词的/有的
爻，卦分开统计


利 - 无攸利，无不利，利见大人，利涉大川，喜
亨 - 亨，元亨，利贞
吉 - 元吉，贞吉，终吉, 征吉，吉，大吉，夙吉
吝 - 吝，贞吝，终吝，
厉 - 厉，贞厉，乱
悔 - 悔亡，有悔，无悔
咎 - 无咎，咎
凶 - 凶，贞凶

"""
