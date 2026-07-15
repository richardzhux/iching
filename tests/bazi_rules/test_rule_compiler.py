from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from iching.core.bazi_rules import compiler as rule_compiler
from iching.core.bazi_rules.compiler import (
    canonical_digest,
    canonical_json_bytes,
    compile_rule_bundle,
    compile_rule_records,
    hydrate_propositions,
    index_hydrated_propositions,
    ingest_rule_definitions,
    load_hydrated_propositions,
)
from iching.core.bazi_rules.fact_graph import build_bazi_fact_graph
from iching.core.bazi_rules.schema import (
    Proposition,
    RuleDefinition,
    SourceLocator,
    SourceSegment,
    SourceWitness,
    TruthValue,
)


ROOT = Path(__file__).resolve().parents[2]


def _source_fixture(
    *,
    witness_allowed: bool = True,
    quote_hash: str | None = None,
    proposition_locator_ids: tuple[str, ...] = ("loc.1",),
    segment_locator_ids: tuple[str, ...] = ("loc.1",),
    claim: str = "官逢財印而無刑沖破害，官格成。",
) -> tuple[Any, ...]:
    quote = "官逢財印又無刑冲破害官格成也"
    witness = SourceWitness(
        "witness.1",
        "1" * 64,
        witness_allowed,
        "public_domain",
        {
            "status": "public_domain",
            "production_use_allowed": witness_allowed,
            "basis": ["fixture public-domain source"],
        },
        ("canonical_textual_authority",),
        "base_witness",
    )
    locator = SourceLocator(
        "loc.1",
        witness.id,
        quote,
        quote_hash or hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        True,
        "scan_verified",
        pdf_page=1,
    )
    segment = SourceSegment(
        "segment.1",
        quote,
        segment_locator_ids,
        "shen_core",
        "formation_rule",
        "scan_verified",
    )
    records = [
        {
            "id": "prop.1",
            "atomic_claim": claim,
            "layer": "shen_core",
            "text_type": "formation",
            "explicit_conditions": ["正官格"],
            "inferred_conditions": [],
            "exceptions": [],
            "segment_ids": ["segment.1"],
            "locator_ids": list(proposition_locator_ids),
            "production_eligible": True,
            "review_state": "scan_verified",
            "chapter_id": "chapter.1",
        }
    ]
    propositions = hydrate_propositions(
        records,
        witnesses=[witness],
        locators=[locator],
        segments=[segment],
        source_manifest_digest="a" * 64,
        corpus_manifest_digest="b" * 64,
        corpus_artifact_digest="c" * 64,
    )
    return propositions, witness, locator, segment, records


def _rule(
    rule_id: str = "rule.1",
    proposition_id: str = "prop.1",
    *,
    slot: str = "formation",
    precedence: int | None = 10,
    predicate: dict[str, Any] | None = None,
    after: tuple[str, ...] = (),
    before: tuple[str, ...] = (),
) -> RuleDefinition:
    return RuleDefinition(
        id=rule_id,
        proposition_id=proposition_id,
        predicate=predicate
        or {
            "op": "all",
            "children": [
                {"op": "month_command_equals", "level": "main", "god": "正官"},
                {"op": "god_exposed", "gods": ["正财", "偏财"]},
            ],
        },
        effect="formation",
        resolution_slot=slot,
        precedence=precedence,
        after=after,
        before=before,
    )


def _prop_map(*propositions: Any) -> dict[str, Any]:
    return {item.id: item for item in propositions}


def test_checked_in_vertical_corpus_hydrates_all_propositions_with_artifact_digest() -> (
    None
):
    propositions = load_hydrated_propositions(
        ROOT / "research/classics/sources/manifest.json",
        ROOT / "research/classics/ziping_zhenquan/manifest.json",
    )

    assert len(propositions) == 85
    assert len({item.id for item in propositions}) == 85
    assert all(
        item.locators and item.segments and item.witnesses for item in propositions
    )
    assert all(len(item.corpus_artifact_digest) == 64 for item in propositions)


def test_compiler_is_deterministic_under_rule_ast_and_membership_reordering() -> None:
    propositions, *_ = _source_fixture()
    second_prop = replace(propositions[0], id="prop.2", atomic_claim="財能生官。")
    first = _rule(
        "rule.a",
        "prop.1",
        slot="formation.a",
        predicate={
            "op": "all",
            "children": [
                {
                    "op": "fact_in",
                    "path": "month_command.main_god",
                    "values": ["七杀", "正官"],
                },
                {"op": "god_exposed", "gods": ["偏财", "正财"]},
            ],
        },
    )
    second = _rule(
        "rule.b",
        "prop.2",
        slot="formation.b",
        predicate={
            "op": "fact_equals",
            "path": "day_master.element",
            "value": "木",
        },
    )
    shuffled_first = replace(
        first,
        predicate={
            "op": "all",
            "children": [
                {"op": "god_exposed", "gods": ["正财", "偏财"]},
                {
                    "op": "fact_in",
                    "path": "month_command.main_god",
                    "values": ["正官", "七杀"],
                },
            ],
        },
    )

    bundle_one = compile_rule_bundle(
        [first, second], _prop_map(propositions[0], second_prop)
    )
    bundle_two = compile_rule_bundle(
        [second, shuffled_first], _prop_map(second_prop, propositions[0])
    )

    assert bundle_one.digest == bundle_two.digest
    assert [item.id for item in bundle_one.rules] == [
        item.id for item in bundle_two.rules
    ]


def test_compiler_digest_changes_for_semantic_rule_or_source_change() -> None:
    propositions, *_ = _source_fixture()
    baseline = compile_rule_bundle([_rule()], _prop_map(*propositions))
    semantic = compile_rule_bundle(
        [
            _rule(
                predicate={
                    "op": "fact_equals",
                    "path": "day_master.element",
                    "value": "火",
                }
            )
        ],
        _prop_map(*propositions),
    )
    changed = replace(propositions[0], corpus_artifact_digest="d" * 64)
    changed_source = compile_rule_bundle([_rule()], _prop_map(changed))

    assert len({baseline.digest, semantic.digest, changed_source.digest}) == 3


def test_every_hydrated_source_field_that_supports_a_rule_changes_the_digest() -> None:
    propositions, *_ = _source_fixture()
    original = propositions[0]
    baseline = compile_rule_bundle([_rule()], _prop_map(original)).digest
    changed_witness = replace(
        original,
        witnesses=(
            replace(
                original.witnesses[0],
                rights={**dict(original.witnesses[0].rights), "caveat": "changed"},
            ),
        ),
    )
    changed_segment = replace(
        original,
        segments=(
            replace(
                original.segments[0],
                diplomatic_text=original.segments[0].diplomatic_text + "。",
            ),
        ),
    )
    changed_locator = replace(
        original,
        locators=(replace(original.locators[0], pdf_page=2),),
    )
    changed_authority = replace(
        original,
        witnesses=(replace(original.witnesses[0], relation="comparison_witness"),),
    )

    digests = {
        baseline,
        compile_rule_bundle([_rule()], _prop_map(changed_witness)).digest,
        compile_rule_bundle([_rule()], _prop_map(changed_segment)).digest,
        compile_rule_bundle([_rule()], _prop_map(changed_locator)).digest,
        compile_rule_bundle([_rule()], _prop_map(changed_authority)).digest,
    }
    assert len(digests) == 5


def test_compiled_bundle_evaluates_to_truth_with_source_trace() -> None:
    propositions, *_ = _source_fixture()
    bundle = compile_rule_bundle([_rule()], _prop_map(*propositions))
    graph = build_bazi_fact_graph(
        [
            {"label": "年", "stem": "庚", "branch": "寅"},
            {"label": "月", "stem": "乙", "branch": "酉"},
            {"label": "日", "stem": "甲", "branch": "午"},
            {"label": "时", "stem": "戊", "branch": "辰"},
        ]
    )

    result = bundle.evaluate(graph)[0]

    assert result.truth is TruthValue.TRUE
    assert result.proposition_id == "prop.1"
    assert result.trace.as_dict()["operator"] == "all"


def test_duplicate_ids_are_rejected_before_mapping_loss() -> None:
    propositions, *_ = _source_fixture()

    with pytest.raises(ValueError, match="duplicate rule"):
        compile_rule_bundle([_rule(), _rule()], _prop_map(*propositions))
    with pytest.raises(ValueError, match="duplicate proposition"):
        index_hydrated_propositions([propositions[0], propositions[0]])


def test_public_compile_api_is_strict_and_ingestion_is_separate() -> None:
    propositions, *_ = _source_fixture()
    raw = {
        "id": "rule.1",
        "proposition_id": "prop.1",
        "predicate": {"op": "fact_equals", "path": "day_master.element", "value": "木"},
        "effect": "formation",
        "resolution_slot": "formation",
        "precedence": 1,
        "execution_ready": True,
        "production_eligible": True,
        "semantic_status": "resolved",
    }

    with pytest.raises(TypeError, match="RuleDefinition"):
        compile_rule_bundle([raw], _prop_map(*propositions))  # type: ignore[list-item]
    with pytest.raises(TypeError, match="mapping"):
        compile_rule_bundle([_rule()], propositions)  # type: ignore[arg-type]
    assert compile_rule_records([raw], list(propositions)).rules[0].id == "rule.1"


@pytest.mark.parametrize(
    ("rules", "message"),
    [
        ([_rule(precedence=None)], "unresolved precedence"),
        ([_rule(after=("missing",))], "missing predecessor"),
        ([_rule(after=("rule.1",))], "self precedence"),
        ([_rule("rule.a"), _rule("rule.b")], "same-slot conflict"),
        (
            [_rule("rule.a", after=("rule.b",)), _rule("rule.b", after=("rule.a",))],
            "cycle",
        ),
    ],
)
def test_precedence_contract_rejects_unresolved_missing_self_conflicting_and_cyclic_rules(
    rules: list[RuleDefinition], message: str
) -> None:
    propositions, *_ = _source_fixture()
    proposition_two = replace(propositions[0], id="prop.2")
    normalized = [
        replace(rule, proposition_id="prop.2") if rule.id == "rule.b" else rule
        for rule in rules
    ]

    with pytest.raises(ValueError, match=message):
        compile_rule_bundle(normalized, _prop_map(propositions[0], proposition_two))


def test_explicit_same_slot_order_resolves_equal_precedence() -> None:
    propositions, *_ = _source_fixture()
    proposition_two = replace(propositions[0], id="prop.2")
    rules = [
        _rule("rule.a", "prop.1", before=("rule.b",)),
        _rule("rule.b", "prop.2", after=("rule.a",)),
    ]

    bundle = compile_rule_bundle(rules, _prop_map(propositions[0], proposition_two))

    assert [item.id for item in bundle.rules] == ["rule.a", "rule.b"]


@pytest.mark.parametrize(
    "mutation",
    [
        "unresolved",
        "source_less",
        "not_reviewed",
        "rights",
        "quote_hash",
        "outside_segment",
    ],
)
def test_production_rules_reject_unresolved_or_invalid_source_evidence(
    mutation: str,
) -> None:
    if mutation == "quote_hash":
        with pytest.raises(ValueError, match="quote hash"):
            _source_fixture(quote_hash="0" * 64)
        return
    if mutation == "outside_segment":
        with pytest.raises(ValueError, match="unknown locator"):
            _source_fixture(segment_locator_ids=("other",))
        return
    propositions, *_ = _source_fixture(witness_allowed=mutation != "rights")
    rule = _rule()
    if mutation == "unresolved":
        rule = replace(
            rule,
            execution_ready=False,
            semantic_status="requires_predicate_definitions",
        )
    elif mutation == "source_less":
        propositions = (replace(propositions[0], locators=()),)
    elif mutation == "not_reviewed":
        propositions = (replace(propositions[0], review_state="draft"),)

    with pytest.raises(ValueError):
        compile_rule_bundle([rule], _prop_map(*propositions))


def test_checked_in_unresolved_candidates_cannot_be_coerced_into_production_rules() -> (
    None
):
    propositions, *_ = _source_fixture()
    candidate = {
        "id": "candidate.1",
        "proposition_id": "prop.1",
        "predicate": {"op": "fact_equals", "path": "day_master.element", "value": "木"},
        "effect": "formation",
        "resolution_slot": "formation",
        "precedence": 1,
        "execution_ready": False,
        "production_eligible": True,
        "semantic_status": "requires_predicate_definitions",
    }

    with pytest.raises(ValueError, match="unresolved or non-executable"):
        compile_rule_records([candidate], list(propositions))


@pytest.mark.parametrize(
    ("target", "field"),
    [
        ("rule_ready", "execution_ready"),
        ("rule_eligible", "production_eligible"),
        ("proposition", "production_eligible"),
        ("witness", "production_use_allowed"),
        ("locator", "visually_verified"),
    ],
)
def test_all_boolean_contracts_reject_truthy_strings(target: str, field: str) -> None:
    propositions, *_ = _source_fixture()
    proposition = propositions[0]
    rule = _rule()
    if target == "rule_ready":
        rule = replace(rule, execution_ready="true")  # type: ignore[arg-type]
    elif target == "rule_eligible":
        rule = replace(rule, production_eligible=1)  # type: ignore[arg-type]
    elif target == "proposition":
        proposition = replace(proposition, production_eligible="true")  # type: ignore[arg-type]
    elif target == "witness":
        proposition = replace(
            proposition,
            witnesses=(
                replace(proposition.witnesses[0], production_use_allowed="true"),
            ),  # type: ignore[arg-type]
        )
    else:
        proposition = replace(
            proposition,
            locators=(replace(proposition.locators[0], visually_verified=1),),  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match=field):
        compile_rule_bundle([rule], _prop_map(proposition))


def test_raw_source_boolean_fields_are_strict_during_hydration() -> None:
    propositions, witness, locator, segment, records = _source_fixture()
    del propositions
    bad = [{**records[0], "production_eligible": "false"}]
    with pytest.raises(ValueError, match="production_eligible"):
        hydrate_propositions(
            bad,
            witnesses=[witness],
            locators=[locator],
            segments=[segment],
            source_manifest_digest="a" * 64,
            corpus_manifest_digest="b" * 64,
            corpus_artifact_digest="c" * 64,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "locator_ids",
        "segment_ids",
        "locator_review",
        "segment_example",
        "proposition_example",
        "comparison_witness",
    ],
)
def test_production_evidence_must_exactly_match_and_be_rule_grade(
    mutation: str,
) -> None:
    propositions, *_ = _source_fixture()
    proposition = propositions[0]
    if mutation == "locator_ids":
        proposition = replace(proposition, locator_ids=("loc.other",))
    elif mutation == "segment_ids":
        proposition = replace(proposition, segment_ids=("segment.other",))
    elif mutation == "locator_review":
        proposition = replace(
            proposition,
            locators=(
                replace(
                    proposition.locators[0],
                    review_state="scan_verified_comparison_only",
                ),
            ),
        )
    elif mutation == "segment_example":
        proposition = replace(
            proposition,
            segments=(
                replace(
                    proposition.segments[0],
                    layer="example",
                    text_type="classical_example",
                ),
            ),
        )
    elif mutation == "proposition_example":
        proposition = replace(proposition, text_type="example_claim")
    else:
        proposition = replace(
            proposition,
            witnesses=(
                replace(proposition.witnesses[0], production_use_allowed=False),
            ),
        )

    with pytest.raises(ValueError):
        compile_rule_bundle([_rule()], _prop_map(proposition))


def test_declared_source_id_arrays_reject_duplicates_during_hydration() -> None:
    propositions, witness, locator, segment, records = _source_fixture()
    del propositions
    duplicate = [{**records[0], "locator_ids": ["loc.1", "loc.1"]}]

    with pytest.raises(ValueError, match="duplicate locator_ids"):
        hydrate_propositions(
            duplicate,
            witnesses=[witness],
            locators=[locator],
            segments=[segment],
            source_manifest_digest="a" * 64,
            corpus_manifest_digest="b" * 64,
            corpus_artifact_digest="c" * 64,
        )


def test_canonical_digest_rejects_nan_and_normalizes_unicode() -> None:
    assert canonical_digest({"x": "é"}) == canonical_digest({"x": "e\u0301"})
    with pytest.raises(ValueError):
        canonical_digest({"x": float("nan")})


@pytest.mark.parametrize(
    "value",
    [
        {1: "not a string key"},
        {"items": {"unordered"}},
        {"é": 1, "e\u0301": 2},
    ],
)
def test_canonical_json_rejects_non_json_keys_sets_and_normalized_collisions(
    value: Any,
) -> None:
    with pytest.raises(ValueError):
        canonical_json_bytes(value)


def test_rule_and_compiled_metadata_are_deeply_frozen() -> None:
    propositions, *_ = _source_fixture()
    metadata = {"nested": {"labels": ["a", "b"]}}
    rule = replace(_rule(), metadata=metadata)
    metadata["nested"]["labels"].append("external")
    bundle = compile_rule_bundle([rule], _prop_map(*propositions))

    assert bundle.rules[0].metadata["nested"]["labels"] == ("a", "b")
    with pytest.raises(TypeError):
        bundle.rules[0].metadata["nested"]["new"] = True  # type: ignore[index]


def test_caller_owned_rule_and_provenance_inputs_are_snapshot_immutable() -> None:
    propositions, *_ = _source_fixture()
    original = propositions[0]
    predicate_values = ["木"]
    predicate = {
        "op": "fact_in",
        "path": "day_master.element",
        "values": predicate_values,
    }
    rights = {
        "status": "public_domain",
        "production_use_allowed": True,
        "basis": ["immutable fixture"],
    }
    roles = ["canonical_textual_authority"]
    witness = SourceWitness(
        "witness.1",
        "1" * 64,
        True,
        "public_domain",
        rights,
        roles,  # type: ignore[arg-type]
        "base_witness",
    )
    segment_locator_ids = ["loc.1"]
    segment = SourceSegment(
        "segment.1",
        original.segments[0].diplomatic_text,
        segment_locator_ids,  # type: ignore[arg-type]
        "shen_core",
        "formation_rule",
        "scan_verified",
    )
    explicit_conditions = ["正官格"]
    locators = list(original.locators)
    segments = [segment]
    witnesses = [witness]
    proposition = Proposition(
        id="prop.1",
        atomic_claim=original.atomic_claim,
        layer="shen_core",
        text_type="formation",
        explicit_conditions=explicit_conditions,  # type: ignore[arg-type]
        inferred_conditions=[],  # type: ignore[arg-type]
        exceptions=[],  # type: ignore[arg-type]
        segment_ids=["segment.1"],  # type: ignore[arg-type]
        locator_ids=["loc.1"],  # type: ignore[arg-type]
        locators=locators,  # type: ignore[arg-type]
        segments=segments,  # type: ignore[arg-type]
        witnesses=witnesses,  # type: ignore[arg-type]
        source_manifest_digest="a" * 64,
        corpus_manifest_digest="b" * 64,
        corpus_artifact_digest="c" * 64,
        production_eligible=True,
        review_state="scan_verified",
        chapter_id="chapter.1",
    )
    rule = _rule(predicate=predicate)
    bundle = compile_rule_bundle([rule], {"prop.1": proposition})
    graph = build_bazi_fact_graph(
        [
            {"label": "年", "stem": "庚", "branch": "寅"},
            {"label": "月", "stem": "乙", "branch": "酉"},
            {"label": "日", "stem": "甲", "branch": "午"},
            {"label": "时", "stem": "戊", "branch": "辰"},
        ]
    )
    digest = bundle.digest

    predicate_values.append("火")
    rights["basis"].append("external mutation")
    roles.append("search_aid")
    segment_locator_ids.append("loc.other")
    explicit_conditions.append("external mutation")
    locators.clear()
    segments.clear()
    witnesses.clear()

    assert bundle.digest == digest
    assert bundle.evaluate(graph)[0].truth is TruthValue.TRUE
    assert bundle.rules[0].predicate.arguments["values"] == ("木",)
    assert bundle.rules[0].proposition.explicit_conditions == ("正官格",)
    assert bundle.rules[0].proposition.segments[0].locator_ids == ("loc.1",)
    assert bundle.rules[0].proposition.witnesses[0].rights["basis"] == (
        "immutable fixture",
    )


def test_nfc_identifiers_resolve_and_normalized_collisions_reject() -> None:
    propositions, *_ = _source_fixture()
    composed_id = "prép"
    decomposed_id = "pre\u0301p"
    proposition = replace(propositions[0], id=composed_id)
    rule = replace(_rule(), proposition_id=decomposed_id)

    bundle = compile_rule_bundle([rule], {decomposed_id: proposition})
    assert bundle.rules[0].proposition_id == composed_id

    with pytest.raises(ValueError, match="NFC normalization"):
        compile_rule_bundle(
            [rule],
            {composed_id: proposition, decomposed_id: proposition},
        )
    with pytest.raises(ValueError, match="duplicate rule"):
        compile_rule_bundle(
            [
                replace(rule, id="rulé"),
                replace(rule, id="rule\u0301"),
            ],
            {composed_id: proposition},
        )


def test_precedence_declaration_aliases_and_redundant_edges_have_one_digest() -> None:
    propositions, *_ = _source_fixture()
    props = tuple(replace(propositions[0], id=f"prop.{index}") for index in range(3))
    canonical = [
        _rule("rule.a", "prop.0", slot="slot.a", before=("rule.b",)),
        _rule("rule.b", "prop.1", slot="slot.b", before=("rule.c",)),
        _rule("rule.c", "prop.2", slot="slot.c"),
    ]
    aliased = [
        _rule(
            "rule.a",
            "prop.0",
            slot="slot.a",
            before=("rule.b", "rule.c"),
        ),
        _rule(
            "rule.b",
            "prop.1",
            slot="slot.b",
            after=("rule.a",),
            before=("rule.c",),
        ),
        _rule("rule.c", "prop.2", slot="slot.c", after=("rule.b",)),
    ]

    first = compile_rule_bundle(canonical, _prop_map(*props))
    second = compile_rule_bundle(aliased, _prop_map(*props))

    assert first.digest == second.digest
    assert [(rule.after, rule.before) for rule in first.rules] == [
        (rule.after, rule.before) for rule in second.rules
    ]


def test_transitive_same_slot_numeric_contradiction_rejects() -> None:
    propositions, *_ = _source_fixture()
    props = tuple(replace(propositions[0], id=f"prop.{index}") for index in range(3))
    rules = [
        _rule(
            "rule.a",
            "prop.0",
            slot="formation",
            precedence=20,
            before=("rule.b",),
        ),
        _rule(
            "rule.b",
            "prop.1",
            slot="bridge",
            precedence=5,
            before=("rule.c",),
        ),
        _rule("rule.c", "prop.2", slot="formation", precedence=10),
    ]

    with pytest.raises(ValueError, match="transitive edge"):
        compile_rule_bundle(rules, _prop_map(*props))


def test_raw_rule_ingestion_rejects_coercion_and_noncanonical_input() -> None:
    base: dict[Any, Any] = {
        "id": "rule.1",
        "proposition_id": "prop.1",
        "predicate": {"op": "fact_equals", "path": "day_master.element", "value": "木"},
        "effect": "formation",
        "resolution_slot": "formation",
        "precedence": 1,
        "execution_ready": True,
        "production_eligible": True,
        "semantic_status": "resolved",
    }
    non_string_key = dict(base)
    non_string_key[1] = "bad"
    missing = dict(base)
    del missing["effect"]
    bad_records = [
        {**base, "id": 1},
        {**base, "effect": 1},
        {**base, "after": "rule.other"},
        {**base, "after": ["rule.other", "rule.other"]},
        {**base, "precedence": True},
        {**base, "precedence": 1.5},
        {**base, "metadata": {"bad": {"set"}}},
        non_string_key,
        missing,
    ]

    for record in bad_records:
        with pytest.raises((TypeError, ValueError)):
            ingest_rule_definitions([record])


def test_raw_proposition_sequences_reject_strings_instead_of_coercing() -> None:
    propositions, witness, locator, segment, records = _source_fixture()
    del propositions
    bad = [{**records[0], "explicit_conditions": "正官格"}]

    with pytest.raises(ValueError, match="sequence of strings"):
        hydrate_propositions(
            bad,
            witnesses=[witness],
            locators=[locator],
            segments=[segment],
            source_manifest_digest="a" * 64,
            corpus_manifest_digest="b" * 64,
            corpus_artifact_digest="c" * 64,
        )


def test_raw_proposition_records_reject_unknown_semantic_fields() -> None:
    _, witness, locator, segment, records = _source_fixture()
    typo = [{**records[0], "exception": []}]

    with pytest.raises(ValueError, match="unknown fields.*exception"):
        hydrate_propositions(
            typo,
            witnesses=[witness],
            locators=[locator],
            segments=[segment],
            source_manifest_digest="a" * 64,
            corpus_manifest_digest="b" * 64,
            corpus_artifact_digest="c" * 64,
        )


def test_empty_unsupported_or_search_only_evidence_cannot_compile() -> None:
    propositions, *_ = _source_fixture()
    original = propositions[0]
    empty_quote = replace(
        original.locators[0],
        quote="",
        quote_sha256=hashlib.sha256(b"").hexdigest(),
    )
    with pytest.raises(ValueError, match="meaningful source coordinate"):
        replace(original.locators[0], pdf_page=None, bbox=None, url=None)
    cases = [
        replace(original, atomic_claim=" "),
        replace(
            original,
            segments=(replace(original.segments[0], diplomatic_text=" "),),
        ),
        replace(original, locators=(empty_quote,)),
        replace(
            original,
            segments=(replace(original.segments[0], layer="example"),),
        ),
        replace(
            original,
            witnesses=(replace(original.witnesses[0], rights={}),),
        ),
        replace(
            original,
            witnesses=(
                replace(
                    original.witnesses[0],
                    authority_roles=("search_aid", "comparison_only"),
                ),
            ),
        ),
    ]

    for proposition in cases:
        with pytest.raises(ValueError):
            compile_rule_bundle([_rule()], _prop_map(proposition))


def test_source_segment_rejects_duplicate_locator_ids() -> None:
    with pytest.raises(ValueError, match="duplicate locator_ids"):
        SourceSegment(
            "segment.1",
            "source",
            ("loc.1", "loc.1"),
            "shen_core",
            "formation_rule",
            "scan_verified",
        )


def test_proposition_rejects_duplicate_witness_ids_before_mapping() -> None:
    propositions, *_ = _source_fixture()
    proposition = propositions[0]

    with pytest.raises(ValueError, match="duplicate witness"):
        replace(
            proposition,
            witnesses=(proposition.witnesses[0], proposition.witnesses[0]),
        )


def _contextual_source_fixture(
    *,
    context_quote: str = "comparison reading",
    context_quote_hash: str | None = None,
    context_witness_id: str = "witness.context",
    segment_locator_ids: tuple[str, ...] = ("loc.1", "loc.context"),
) -> tuple[Any, ...]:
    _, witness, locator, segment, records = _source_fixture()
    context_witness = SourceWitness(
        "witness.context",
        "2" * 64,
        False,
        "rights_unresolved",
        {
            "status": "rights_unresolved",
            "production_use_allowed": False,
            "basis": ["comparison only"],
        },
        ("comparison_only",),
        "comparison_witness",
    )
    context_locator = SourceLocator(
        "loc.context",
        context_witness_id,
        context_quote,
        context_quote_hash or hashlib.sha256(context_quote.encode("utf-8")).hexdigest(),
        True,
        "scan_verified_comparison_only",
        pdf_page=2,
    )
    contextual_segment = replace(segment, locator_ids=segment_locator_ids)
    return (
        records,
        witness,
        locator,
        contextual_segment,
        context_witness,
        context_locator,
    )


def test_hydration_preserves_context_locators_without_applying_support_rights_gate() -> (
    None
):
    (
        records,
        witness,
        locator,
        segment,
        context_witness,
        context_locator,
    ) = _contextual_source_fixture()
    propositions = hydrate_propositions(
        records,
        witnesses=[witness, context_witness],
        locators=[locator, context_locator],
        segments=[segment],
        source_manifest_digest="a" * 64,
        corpus_manifest_digest="b" * 64,
        corpus_artifact_digest="c" * 64,
    )

    proposition = propositions[0]
    assert proposition.locators == (locator,)
    assert proposition.context_locators == (context_locator,)
    assert proposition.context_witnesses == (context_witness,)
    baseline = compile_rule_bundle([_rule()], _prop_map(proposition)).digest

    changed_quote = "changed comparison reading"
    changed_context = replace(
        context_locator,
        quote=changed_quote,
        quote_sha256=hashlib.sha256(changed_quote.encode("utf-8")).hexdigest(),
    )
    changed = hydrate_propositions(
        records,
        witnesses=[witness, context_witness],
        locators=[locator, changed_context],
        segments=[segment],
        source_manifest_digest="a" * 64,
        corpus_manifest_digest="b" * 64,
        corpus_artifact_digest="c" * 64,
    )[0]
    assert compile_rule_bundle([_rule()], _prop_map(changed)).digest != baseline


def test_each_production_segment_requires_eligible_support_locator() -> None:
    (
        records,
        witness,
        locator,
        segment,
        context_witness,
        context_locator,
    ) = _contextual_source_fixture()
    context_only_segment = replace(
        segment,
        id="segment.2",
        locator_ids=("loc.context",),
    )
    proposition_record = {
        **records[0],
        "segment_ids": ["segment.1", "segment.2"],
    }
    proposition = hydrate_propositions(
        [proposition_record],
        witnesses=[witness, context_witness],
        locators=[locator, context_locator],
        segments=[segment, context_only_segment],
        source_manifest_digest="a" * 64,
        corpus_manifest_digest="b" * 64,
        corpus_artifact_digest="c" * 64,
    )[0]

    with pytest.raises(
        ValueError, match="segment segment.2 has no production support locator"
    ):
        compile_rule_bundle([_rule()], _prop_map(proposition))

    covered_segment = replace(
        context_only_segment,
        locator_ids=("loc.context", "loc.1"),
    )
    covered = hydrate_propositions(
        [proposition_record],
        witnesses=[witness, context_witness],
        locators=[locator, context_locator],
        segments=[segment, covered_segment],
        source_manifest_digest="a" * 64,
        corpus_manifest_digest="b" * 64,
        corpus_artifact_digest="c" * 64,
    )[0]
    assert compile_rule_bundle([_rule()], _prop_map(covered)).rules[0].id == "rule.1"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("unknown_locator", "unknown locator"),
        ("bad_quote_hash", "quote hash"),
        ("unknown_witness", "unknown witness"),
    ],
)
def test_every_segment_locator_resolves_and_validates_during_hydration(
    mutation: str, message: str
) -> None:
    kwargs: dict[str, Any] = {}
    if mutation == "unknown_locator":
        kwargs["segment_locator_ids"] = ("loc.1", "loc.missing")
    elif mutation == "bad_quote_hash":
        kwargs["context_quote_hash"] = "0" * 64
    else:
        kwargs["context_witness_id"] = "witness.missing"
    records, witness, locator, segment, context_witness, context_locator = (
        _contextual_source_fixture(**kwargs)
    )

    with pytest.raises(ValueError, match=message):
        hydrate_propositions(
            records,
            witnesses=[witness, context_witness],
            locators=[locator, context_locator],
            segments=[segment],
            source_manifest_digest="a" * 64,
            corpus_manifest_digest="b" * 64,
            corpus_artifact_digest="c" * 64,
        )


@pytest.mark.parametrize(
    "field",
    ["explicit_conditions", "inferred_conditions", "exceptions"],
)
def test_typed_proposition_conditions_are_strict_nfc_string_snapshots(
    field: str,
) -> None:
    propositions, *_ = _source_fixture()
    proposition = propositions[0]

    with pytest.raises(TypeError, match=field):
        replace(proposition, **{field: ({"nested": "not a string"},)})
    with pytest.raises(TypeError, match=field):
        replace(proposition, **{field: "not a condition sequence"})
    with pytest.raises(ValueError, match=field):
        replace(proposition, **{field: (" \t",)})

    caller_owned = ["e\u0301", "f"]
    normalized = replace(proposition, **{field: caller_owned})
    caller_owned.append("external mutation")
    assert getattr(normalized, field) == ("é", "f")


def test_condition_sets_normalize_before_digest_sorting() -> None:
    propositions, *_ = _source_fixture()
    proposition = propositions[0]
    composed = replace(proposition, explicit_conditions=("é", "f"))
    decomposed = replace(proposition, explicit_conditions=("f", "e\u0301"))

    assert compile_rule_bundle([_rule()], _prop_map(composed)).digest == (
        compile_rule_bundle([_rule()], _prop_map(decomposed)).digest
    )


@pytest.mark.parametrize(
    "bbox",
    [
        (0, 1, 2),
        (0, 1, 2, True),
        (0, 1, 2, float("nan")),
        (0, 1, 2, "3"),
        (0, 1, 2, 3 + 0j),
    ],
)
def test_typed_source_locator_bbox_requires_four_finite_real_non_bool_numbers(
    bbox: tuple[Any, ...],
) -> None:
    _, _, locator, *_ = _source_fixture()

    with pytest.raises((TypeError, ValueError), match="bbox"):
        replace(locator, pdf_page=None, bbox=bbox)


@pytest.mark.parametrize(
    "url",
    [
        "relative/source",
        "ftp://example.com/source",
        "https:///missing-host",
        " https://example.com/source",
        "https://exa mple.com/source",
        "https://exa\u00a0mple.com/source",
        "https://example.com:bad/source",
    ],
)
def test_typed_source_locator_requires_a_meaningful_absolute_web_coordinate(
    url: str,
) -> None:
    _, _, locator, *_ = _source_fixture()

    with pytest.raises(ValueError, match="URL|url"):
        replace(locator, pdf_page=None, url=url)
    with pytest.raises(ValueError, match="coordinate"):
        replace(locator, pdf_page=None, url=None)

    assert (
        replace(
            locator,
            pdf_page=None,
            url="https://example.com/source",
        ).url
        == "https://example.com/source"
    )


def test_json_and_jsonl_loaders_reject_duplicate_object_keys(tmp_path: Path) -> None:
    json_path = tmp_path / "duplicate.json"
    json_path.write_text('{"outer":{"same":1,"same":2}}\n', encoding="utf-8")
    jsonl_path = tmp_path / "duplicate.jsonl"
    jsonl_path.write_text('{"same":1,"same":2}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate object key"):
        rule_compiler._load_json(json_path)
    with pytest.raises(ValueError, match="duplicate object key"):
        rule_compiler._load_jsonl(jsonl_path)


def test_sequence_ingestion_snapshots_one_shot_iterables_exactly_once() -> None:
    propositions, witness, locator, segment, records = _source_fixture()
    hydrated = hydrate_propositions(
        (record for record in records),  # type: ignore[arg-type]
        witnesses=(item for item in (witness,)),  # type: ignore[arg-type]
        locators=(item for item in (locator,)),  # type: ignore[arg-type]
        segments=(item for item in (segment,)),  # type: ignore[arg-type]
        source_manifest_digest="a" * 64,
        corpus_manifest_digest="b" * 64,
        corpus_artifact_digest="c" * 64,
    )
    assert [item.id for item in hydrated] == ["prop.1"]
    assert list(
        index_hydrated_propositions(  # type: ignore[arg-type]
            (item for item in propositions)
        )
    ) == ["prop.1"]
    assert (
        compile_rule_bundle(  # type: ignore[arg-type]
            (item for item in (_rule(),)), _prop_map(*propositions)
        )
        .rules[0]
        .id
        == "rule.1"
    )
    assert (
        compile_rule_records(  # type: ignore[arg-type]
            (item for item in (_rule(),)),
            (item for item in propositions),
        )
        .rules[0]
        .id
        == "rule.1"
    )


def test_manifest_semantic_digests_ignore_only_id_addressed_array_order(
    tmp_path: Path,
) -> None:
    source_path = ROOT / "research/classics/sources/manifest.json"
    corpus_path = ROOT / "research/classics/ziping_zhenquan/manifest.json"
    baseline = load_hydrated_propositions(source_path, corpus_path)

    source = json.loads(source_path.read_text(encoding="utf-8"))
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    source["witnesses"].reverse()
    source["search_aids"].reverse()
    corpus["locators"].reverse()
    corpus["chapters"].reverse()
    corpus["witness_variants"].reverse()
    reordered_source = tmp_path / "source.json"
    reordered_corpus = tmp_path / "corpus.json"
    reordered_source.write_text(
        json.dumps(source, ensure_ascii=False), encoding="utf-8"
    )
    reordered_corpus.write_text(
        json.dumps(corpus, ensure_ascii=False), encoding="utf-8"
    )

    reordered = load_hydrated_propositions(reordered_source, reordered_corpus)
    assert sorted(item.id for item in reordered) == sorted(item.id for item in baseline)
    assert reordered[0].source_manifest_digest == baseline[0].source_manifest_digest
    assert reordered[0].corpus_manifest_digest == baseline[0].corpus_manifest_digest
    assert reordered[0].corpus_artifact_digest == baseline[0].corpus_artifact_digest

    source["witnesses"][0]["rights"]["basis"].reverse()
    reordered_source.write_text(
        json.dumps(source, ensure_ascii=False), encoding="utf-8"
    )
    semantically_changed = load_hydrated_propositions(
        reordered_source, reordered_corpus
    )
    assert semantically_changed[0].source_manifest_digest != (
        baseline[0].source_manifest_digest
    )


def test_authority_roles_are_set_like_in_source_and_bundle_digests(
    tmp_path: Path,
) -> None:
    source_path = ROOT / "research/classics/sources/manifest.json"
    corpus_path = ROOT / "research/classics/ziping_zhenquan/manifest.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    reordered_source = json.loads(source_path.read_text(encoding="utf-8"))
    target = next(
        witness
        for witness in reordered_source["witnesses"]
        if len(witness["authority_roles"]) > 1
    )
    target["authority_roles"].reverse()
    reordered_path = tmp_path / "source-authority-order.json"
    reordered_path.write_text(
        json.dumps(reordered_source, ensure_ascii=False), encoding="utf-8"
    )

    assert {
        witness.id: witness for witness in rule_compiler._source_witnesses(source)
    } == {
        witness.id: witness
        for witness in rule_compiler._source_witnesses(reordered_source)
    }
    baseline = load_hydrated_propositions(source_path, corpus_path)
    reordered = load_hydrated_propositions(reordered_path, corpus_path)
    assert reordered[0].source_manifest_digest == baseline[0].source_manifest_digest

    proposition_id = "zzq.prop.useful.form-officer-001"
    baseline_proposition = next(item for item in baseline if item.id == proposition_id)
    reordered_proposition = next(
        item for item in reordered if item.id == proposition_id
    )
    rule = replace(_rule(), proposition_id=proposition_id)
    assert (
        compile_rule_bundle([rule], _prop_map(baseline_proposition)).digest
        == compile_rule_bundle([rule], _prop_map(reordered_proposition)).digest
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", ""),
        ("id", " \t"),
        ("proposition_id", ""),
        ("proposition_id", " \t"),
        ("effect", ""),
        ("effect", " \t"),
        ("resolution_slot", ""),
        ("resolution_slot", " \t"),
    ],
)
def test_typed_executable_rule_rejects_blank_identifiers_and_slots(
    field: str, value: str
) -> None:
    with pytest.raises(ValueError, match=field.replace("_", " ")):
        replace(_rule(), **{field: value})


@pytest.mark.parametrize("field", ["id", "proposition_id"])
def test_typed_rule_ids_remain_required_when_execution_is_disabled(field: str) -> None:
    with pytest.raises(ValueError, match=field.replace("_", " ")):
        replace(_rule(), execution_ready=False, **{field: " \t"})
