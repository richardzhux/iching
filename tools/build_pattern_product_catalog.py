"""Build the compact, deployable product index for classical pattern research.

The research JSONL files remain the editorial source of truth. This command
projects them into a small runtime asset that the API can safely expose without
shipping scans or reading the research tree in production.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = ROOT / "research" / "classics" / "ziping_zhenquan"
OUTPUT = ROOT / "src" / "iching" / "core" / "data" / "pattern-product-catalog-v1.json"

CHAPTER_PATTERN_IDS = {
    "zzq.pattern.direct-officer": "direct_officer",
    "zzq.pattern.seven-killings": "seven_killings",
    "zzq.pattern.wealth": "wealth",
    "zzq.pattern.resource": "resource",
    "zzq.pattern.eating-god": "eating_god",
    "zzq.pattern.hurting-officer": "hurting_officer",
    "zzq.pattern.prosperity-robbery": "prosperity_robbery",
    "zzq.pattern.yang-blade": "yang_blade",
    "zzq.pattern.special-gate": "special_gate",
    "zzq.useful-god.success-failure-rescue": "lifecycle",
    "zzq.appendix.pattern-plates": "pattern_plates",
}

PATTERN_LABELS = {
    "direct_officer": "正官格",
    "seven_killings": "七杀格",
    "wealth": "财格",
    "resource": "印格",
    "eating_god": "食神格",
    "hurting_officer": "伤官格",
    "prosperity_robbery": "建禄月劫",
    "yang_blade": "阳刃格",
    "special_gate": "特别格",
    "lifecycle": "用神成败救应",
    "pattern_plates": "格局总表",
}


def read_jsonl(directory: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((RESEARCH_ROOT / directory).glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return rows


def terminal_status(rule: dict[str, Any]) -> str:
    if rule.get("execution_ready"):
        return "executable"
    status = str(rule.get("semantic_status", ""))
    if "witness" in status or not rule.get("production_eligible", False):
        return "example_only"
    if rule.get("effect") in {"ordinary_route_precedence", "special_candidate_rejected"}:
        return "contextual"
    return "deferred"


def compact_rule(rule: dict[str, Any]) -> dict[str, Any]:
    metadata = rule.get("metadata") if isinstance(rule.get("metadata"), dict) else {}
    return {
        "id": rule["id"],
        "chapter_id": rule["chapter_id"],
        "pattern_id": metadata.get("pattern_id") or CHAPTER_PATTERN_IDS.get(rule["chapter_id"], "general"),
        "proposition_id": rule.get("proposition_id"),
        "effect": rule.get("effect"),
        "terminal_status": terminal_status(rule),
        "semantic_status": rule.get("semantic_status"),
        "execution_ready": bool(rule.get("execution_ready")),
    }


def compact_example(example: dict[str, Any]) -> dict[str, Any]:
    pattern_id = CHAPTER_PATTERN_IDS.get(example["chapter_id"], "general")
    return {
        "id": example["id"],
        "chapter_id": example["chapter_id"],
        "pattern_id": pattern_id,
        "name": example.get("name") or "古籍例命",
        "pillars": example.get("pillars", []),
        "author_claim": example.get("author_claim", ""),
        "classification": example.get("source_claim_classification", ""),
        "review_state": example.get("review_state", ""),
        "locator_ids": example.get("locator_ids", []),
    }


def main() -> None:
    rules = [compact_rule(row) for row in read_jsonl("rules")]
    examples = [compact_example(row) for row in read_jsonl("examples")]
    groups = []
    group_ids = sorted({row["pattern_id"] for row in [*rules, *examples]})
    for pattern_id in group_ids:
        group_rules = [row for row in rules if row["pattern_id"] == pattern_id]
        group_examples = [row for row in examples if row["pattern_id"] == pattern_id]
        groups.append(
            {
                "pattern_id": pattern_id,
                "label": PATTERN_LABELS.get(pattern_id, pattern_id),
                "candidate_count": len(group_rules),
                "executable_count": sum(row["execution_ready"] for row in group_rules),
                "example_count": len(group_examples),
                "rules": group_rules,
                "examples": group_examples,
            }
        )

    digest_input = json.dumps(
        {"rules": rules, "examples": examples},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    payload = {
        "version": "pattern-product-catalog-v1",
        "digest": hashlib.sha256(digest_input).hexdigest(),
        "candidate_count": len(rules),
        "example_count": len(examples),
        "status_counts": dict(sorted(Counter(row["terminal_status"] for row in rules).items())),
        "groups": groups,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: "
        f"{len(rules)} candidates, {len(examples)} examples, {payload['status_counts']}"
    )


if __name__ == "__main__":
    main()
