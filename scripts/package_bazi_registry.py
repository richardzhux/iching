"""Rebuild the packaged canonical BaZi registry from reviewed research sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from iching.core.bazi_rules.registry import (
    compile_research_direct_officer_registry,
    registry_to_data,
)



PATTERN_CHAPTERS = (
    ("direct_officer", "正官", "direct-officer"),
    ("direct_resource", "正印", "resource"),
    ("indirect_resource", "偏印", "resource"),
    ("direct_wealth", "正财", "wealth"),
    ("indirect_wealth", "偏财", "wealth"),
    ("eating_god", "食神", "eating-god"),
    ("hurting_officer", "伤官", "hurting-officer"),
    ("seven_killings", "七杀", "seven-killings"),
    ("month_prosperity", "建禄", "prosperity-robbery"),
    ("month_robbery", "月劫", "prosperity-robbery"),
    ("yang_blade", "阳刃", "yang-blade"),
)


def package_coverage(root: Path, compiled: dict) -> None:
    """Ship a source-clause inventory separately from executable verdict rules."""
    corpus = root / "research/classics/ziping_zhenquan"
    def records(folder: str):
        return [json.loads(line) for path in sorted((corpus / folder).glob("*.jsonl"))
                for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rules = records("rules")
    propositions = records("propositions")
    segments = {x["id"]: x for x in records("segments")}
    compiled_ids = {x["id"] for x in compiled["rules"]}
    def reason(rule):
        semantic = rule.get("semantic_status", "")
        if "strength" in semantic or "light_heavy" in semantic:
            return "身强弱、旺衰或根深浅尚无经核定的非数值定义。"
        if "position_safety" in semantic:
            return "原文的财印位置须逐例绑定，不能简化为全局不相克。"
        if "complete_gengcun" in semantic:
            return "本章见证缺少被救对象，不能据残句独立建立救应。"
        if "binding" in semantic or "bound_damage" in semantic:
            return "需把作用星、被伤对象与同一成格路径准确绑定。"
        if "source_alternatives" in semantic:
            return "原文并列路径须拆开，不能合并为一个宽泛条件。"
        if "transformation" in semantic:
            return "变化成立的事实条件尚待核定。"
        if "path" in semantic:
            return "所依赖的成格或制化路径尚未完整定义。"
        if "inference" in semantic:
            return "仍含原文之外的推断条件，需要先裁定其依据。"
        if "special" in semantic:
            return "特殊外格另行审查。"
        return "原文已纳入，判定条件或来源绑定尚待核定。"
    def clause(prop):
        linked = [r for r in rules if r.get("proposition_id") == prop["id"]]
        active = [r["id"] for r in linked if r["id"] in compiled_ids]
        pending = [r for r in linked if r["id"] not in compiled_ids]
        return {"id": prop["id"], "claim": prop["atomic_claim"],
                "layer": prop.get("layer", ""), "review_state": prop.get("review_state", ""),
                "stage": prop.get("text_type", ""), "active_rule_ids": active,
                "pending_reasons": sorted({reason(r) for r in pending}) or
                    ([] if active else ["尚未形成可执行规则；保留原文命题供核对。"]),
                "inferred_conditions": prop.get("inferred_conditions", []),
                "quotes": [segments[s].get("diplomatic_text", "") for s in prop.get("segment_ids", []) if s in segments],
                "locator_ids": prop.get("locator_ids", [])}
    patterns = []
    for pid, label, suffix in PATTERN_CHAPTERS:
        active = [r for r in rules if r["id"] in compiled_ids and r.get("metadata", {}).get("pattern_id") == pid]
        patterns.append({"pattern_id": pid, "label": label,
            "stage_counts": {stage: sum(r.get("metadata", {}).get("stage") == stage for r in active)
                             for stage in ("candidate", "formation", "damage", "rescue")},
            "clauses": [clause(p) for p in propositions if p.get("chapter_id") == "zzq.pattern." + suffix],
            "source_paragraphs": [{"id": seg["id"], "text": seg.get("diplomatic_text", ""),
                "type": seg.get("text_type", ""), "locator_ids": seg.get("locator_ids", [])}
                for seg in segments.values() if seg.get("chapter_id") == "zzq.pattern." + suffix
                and seg.get("layer") == "shen_core"],
            "scope": "partial"})
    payload = {"version": "zzq-ordinary-coverage-2026.09-v1", "patterns": patterns,
        "shared_clauses": [clause(p) for p in propositions if p.get("chapter_id") == "zzq.useful-god.success-failure-rescue"],
        "note": "11类常规格局逐章清点，保留已整理正文段落与已拆分命题；收录原文不表示已实现其中全部条件，规则条数不是完整度。成格出现率受历法分布和已实现路径共同影响，不能据此比较各格本身的稀有程度。候选未成格不等于破格。"}
    target = root / "src/iching/core/data/bazi-pattern-coverage.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.project_root.resolve()
    registry = compile_research_direct_officer_registry(root)
    target = root / "src/iching/core/bazi_rules/bundles/zzq-shen-canonical-v1.json"
    payload = (
        json.dumps(
            registry_to_data(registry),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(target)
    package_coverage(root, registry_to_data(registry))


if __name__ == "__main__":
    main()
