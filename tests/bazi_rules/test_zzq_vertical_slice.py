from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from iching.core.bazi_rules.adapter import evaluate_example_attestations
from iching.core.bazi_rules.engine import evaluate_pattern_lifecycle
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_rules.registry import (
    compile_research_direct_officer_registry,
    load_packaged_attestation_bundle,
    load_packaged_registry,
)
from iching.core.bazi_rules.schema import TruthValue


ROOT = Path(__file__).resolve().parents[2]


def _chart(*texts: str) -> list[dict[str, Any]]:
    return [
        {"label": label, "stem": text[0], "branch": text[1], "text": text}
        for label, text in zip(("年", "月", "日", "时"), texts)
    ]


FIXTURES = {
    "xue": ("甲申", "壬申", "乙巳", "戊寅"),
    "anonymous": ("壬戌", "丁未", "戊申", "乙卯"),
    "jin": ("乙卯", "丁亥", "丁未", "庚戌"),
    "xuan": ("己卯", "辛未", "壬寅", "辛亥"),
    "li": ("庚寅", "乙酉", "甲子", "戊辰"),
    "fan": ("丁丑", "壬寅", "己巳", "丙寅"),
}


@pytest.mark.parametrize(
    ("fixture", "expected", "active_path"),
    [
        ("xue", "formed", "dual_support"),
        ("jin", "formed", "dual_support"),
        ("li", "rescued", "wealth_support"),
        ("anonymous", "undetermined", "wealth_support"),
        ("xuan", "undetermined", "seal_support"),
        ("fan", "formed", "wealth_support"),
    ],
)
def test_direct_officer_vertical_slice_matches_adjudicated_generic_results(
    fixture: str,
    expected: str,
    active_path: str,
) -> None:
    registry = load_packaged_registry()
    context = build_rule_evaluation_context(
        build_bazi_fact_graph(_chart(*FIXTURES[fixture]))
    )

    result = evaluate_pattern_lifecycle(context, registry)

    assert result.status == expected
    assert any(
        item.path_id == active_path and item.status not in {"inactive", "superseded"}
        for item in result.paths
    )
    assert tuple(item.stage for item in result.stages) == (
        "candidate",
        "formation",
        "damage",
        "rescue",
        "purity",
        "transformation",
        "special_gate",
        "resolution",
    )


def test_li_rescue_binds_the_actual_exposed_killing_relation_member() -> None:
    registry = load_packaged_registry()
    result = evaluate_pattern_lifecycle(
        build_rule_evaluation_context(build_bazi_fact_graph(_chart(*FIXTURES["li"]))),
        registry,
    )
    path = next(item for item in result.paths if item.path_id == "wealth_support")

    assert path.actual_damage_ids == ("zzq.rule.officer.damage-mixed-killing-001",)
    assert path.resolved_damage_ids == path.actual_damage_ids
    assert path.active_rescue_ids == ("zzq.rule.useful.rescue-officer-002",)


def test_wealth_controlling_seal_invalidates_that_rescue_on_selected_wealth_path() -> (
    None
):
    registry = load_packaged_registry()
    result = evaluate_pattern_lifecycle(
        build_rule_evaluation_context(
            build_bazi_fact_graph(_chart("癸卯", "己酉", "甲子", "丁卯"))
        ),
        registry,
    )
    path = next(item for item in result.paths if item.path_id == "wealth_support")

    assert result.status == "broken"
    assert path.status == "broken"
    assert path.actual_damage_ids == ("zzq.rule.officer.damage-hurting-officer-001",)
    assert path.unresolved_damage_ids == path.actual_damage_ids
    assert path.invalidated_rescue_ids == ("zzq.rule.officer.rescue-hurting-seal-001",)


def test_hidden_or_element_only_mechanics_keep_kleene_activation_semantics() -> None:
    predicate = {
        "op": "activation_exists",
        "gods": ["伤官"],
        "families": ["output"],
        "positions": [],
        "origins": [],
        "scope": "generic",
    }
    from iching.core.bazi_rules.predicates import evaluate_predicate

    jin = build_rule_evaluation_context(build_bazi_fact_graph(_chart(*FIXTURES["jin"])))
    xuan = build_rule_evaluation_context(
        build_bazi_fact_graph(_chart(*FIXTURES["xuan"]))
    )
    fan_graph = build_bazi_fact_graph(_chart(*FIXTURES["fan"]))

    assert evaluate_predicate(predicate, jin).truth is TruthValue.FALSE
    assert evaluate_predicate(predicate, xuan).truth is TruthValue.UNKNOWN
    assert not any(
        not item.complete and {"巳", "丑"} <= set(item.required_values)
        for item in fan_graph.combinations
    )


def test_exact_attestations_require_all_four_pillars_and_never_change_generic_digest() -> (
    None
):
    registry = load_packaged_registry()
    bundle = load_packaged_attestation_bundle()
    exact_ids = {
        "anonymous": "zzq.attestation.officer.anonymous-lesser-rank",
        "xuan": "zzq.attestation.officer.xuan",
        "fan": "zzq.attestation.officer.fan",
    }
    for fixture, attestation_id in exact_ids.items():
        texts = FIXTURES[fixture]
        matches = evaluate_example_attestations(_chart(*texts), bundle=bundle)
        assert [item["id"] for item in matches] == [attestation_id]
        assert matches[0]["affects_canonical_status"] is False
        for index in range(4):
            mutated = list(texts)
            mutated[index] = "甲子" if texts[index] != "甲子" else "乙丑"
            assert evaluate_example_attestations(_chart(*mutated), bundle=bundle) == []
    assert bundle.generic_bundle_id == registry.bundle_id
    assert registry.bundle_digest == load_packaged_registry().bundle_digest

    inconsistent = _chart(*FIXTURES["fan"])
    inconsistent[0]["stem"] = "己"
    assert evaluate_example_attestations(inconsistent, bundle=bundle) == []


def test_exact_attestations_canonicalize_positions_and_reject_label_conflicts() -> None:
    bundle = load_packaged_attestation_bundle()
    pillars = _chart(*FIXTURES["fan"])
    label_positions = {"年": "year", "月": "month", "日": "day", "时": "hour"}
    positioned = [
        {**pillar, "position": label_positions[pillar["label"]]} for pillar in pillars
    ]
    reordered = [positioned[index] for index in (2, 0, 3, 1)]
    conflicting = [dict(pillar) for pillar in positioned]
    conflicting[0]["position"] = "month"
    conflicting[1]["position"] = "year"

    assert [
        item["id"] for item in evaluate_example_attestations(reordered, bundle=bundle)
    ] == ["zzq.attestation.officer.fan"]
    assert evaluate_example_attestations(conflicting, bundle=bundle) == []


@pytest.mark.parametrize("invalid", [True, 0, None, "false"])
def test_attestation_schema_requires_literal_false(invalid: Any) -> None:
    package = resources.files("iching.core.bazi_rules")
    payload = json.loads(
        package.joinpath(
            "bundles/zzq-direct-officer-example-attestations-v1.json"
        ).read_text(encoding="utf-8")
    )
    payload["attestations"][0]["affects_canonical_status"] = invalid

    from iching.core.bazi_rules.registry import attestation_bundle_from_data

    with pytest.raises(ValueError, match="literal false"):
        attestation_bundle_from_data(payload)


def test_attestation_schema_rejects_non_sexagenary_exact_signatures() -> None:
    package = resources.files("iching.core.bazi_rules")
    payload = json.loads(
        package.joinpath(
            "bundles/zzq-direct-officer-example-attestations-v1.json"
        ).read_text(encoding="utf-8")
    )
    payload["attestations"][0]["pillars"][0] = "甲甲"

    from iching.core.bazi_rules.registry import attestation_bundle_from_data

    with pytest.raises(ValueError, match="four-pillar signature"):
        attestation_bundle_from_data(payload)


def test_research_compilation_matches_self_contained_packaged_bundle() -> None:
    regenerated = compile_research_direct_officer_registry(ROOT)
    packaged = load_packaged_registry()

    assert regenerated.bundle_id == packaged.bundle_id == "zzq-shen-canonical-v1"
    assert regenerated.bundle_digest == packaged.bundle_digest
    assert regenerated.source_bundle_digest == packaged.source_bundle_digest
    assert [item.canonical_data() for item in regenerated.rules] == [
        item.canonical_data() for item in packaged.rules
    ]
    assert all(item.authority_layer == "shen_core" for item in packaged.rules)
    assert all(
        ".example." not in source_id and ".example-" not in source_id
        for item in packaged.rules
        for source_id in item.source_ids
    )


def test_both_bundle_resources_are_importlib_loadable_without_research_paths() -> None:
    package = resources.files("iching.core.bazi_rules")
    generic = package.joinpath("bundles/zzq-shen-canonical-v1.json")
    examples = package.joinpath(
        "bundles/zzq-direct-officer-example-attestations-v1.json"
    )

    assert generic.is_file()
    assert examples.is_file()
    assert "research/" not in generic.read_text(encoding="utf-8")
    assert "research/" not in examples.read_text(encoding="utf-8")


def test_packaged_bundle_loaders_cache_deeply_immutable_records() -> None:
    registry = load_packaged_registry()
    attestations = load_packaged_attestation_bundle()

    assert registry is load_packaged_registry()
    assert attestations is load_packaged_attestation_bundle()
    with pytest.raises(TypeError):
        registry.rules_by_id["new"] = registry.rules[0]  # type: ignore[index]
    with pytest.raises(TypeError):
        registry.rules[0].predicate.arguments["scope"] = "example"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        attestations.attestations[0].explanation = "mutated"  # type: ignore[misc]


def test_packaged_schemas_reject_binding_fields_outside_their_closed_contracts() -> (
    None
):
    package = resources.files("iching.core.bazi_rules")
    registry_payload = json.loads(
        package.joinpath("bundles/zzq-shen-canonical-v1.json").read_text(
            encoding="utf-8"
        )
    )
    attestation_payload = json.loads(
        package.joinpath(
            "bundles/zzq-direct-officer-example-attestations-v1.json"
        ).read_text(encoding="utf-8")
    )
    registry_payload["rules"][0]["arbitrary_binding"] = "forbidden"
    attestation_payload["attestations"][0]["targets_path_ids"] = ["wealth_support"]

    from iching.core.bazi_rules.registry import (
        attestation_bundle_from_data,
        registry_from_data,
    )

    with pytest.raises(ValueError, match="unknown fields"):
        registry_from_data(registry_payload)
    with pytest.raises(ValueError, match="unknown fields"):
        attestation_bundle_from_data(attestation_payload)


def test_packaged_schemas_do_not_coerce_identifier_types() -> None:
    package = resources.files("iching.core.bazi_rules")
    registry_payload = json.loads(
        package.joinpath("bundles/zzq-shen-canonical-v1.json").read_text(
            encoding="utf-8"
        )
    )
    attestation_payload = json.loads(
        package.joinpath(
            "bundles/zzq-direct-officer-example-attestations-v1.json"
        ).read_text(encoding="utf-8")
    )
    registry_payload["bundle_id"] = 7
    registry_payload["bundle_digest"] = ""
    attestation_payload["generic_bundle_id"] = 7
    attestation_payload["bundle_digest"] = ""

    from iching.core.bazi_rules.registry import (
        attestation_bundle_from_data,
        registry_from_data,
    )

    with pytest.raises(ValueError, match="bundle_id"):
        registry_from_data(registry_payload)
    with pytest.raises(ValueError, match="generic_bundle_id"):
        attestation_bundle_from_data(attestation_payload)


def test_packaged_registry_rejects_rule_tampering_with_a_blank_seal() -> None:
    package = resources.files("iching.core.bazi_rules")
    payload = json.loads(
        package.joinpath("bundles/zzq-shen-canonical-v1.json").read_text(
            encoding="utf-8"
        )
    )
    payload["rules"][0]["precedence"] += 1000
    payload["bundle_digest"] = ""

    from iching.core.bazi_rules.registry import registry_from_data

    with pytest.raises(ValueError, match="bundle_digest must be a non-blank"):
        registry_from_data(payload)


def test_packaged_registry_rejects_provenance_tampering_with_blank_seals() -> None:
    package = resources.files("iching.core.bazi_rules")
    payload = json.loads(
        package.joinpath("bundles/zzq-shen-canonical-v1.json").read_text(
            encoding="utf-8"
        )
    )
    payload["source_provenance"][0]["corpus_artifact_digest"] = "0" * 64
    payload["source_provenance_digest"] = ""
    payload["bundle_digest"] = ""

    from iching.core.bazi_rules.registry import registry_from_data

    with pytest.raises(ValueError, match="source_provenance_digest must be a non-blank"):
        registry_from_data(payload)


def test_packaged_registry_loader_rejects_synthetic_fixture_rules() -> None:
    package = resources.files("iching.core.bazi_rules")
    payload = json.loads(
        package.joinpath("bundles/zzq-shen-canonical-v1.json").read_text(
            encoding="utf-8"
        )
    )
    payload["bundle_digest"] = ""
    payload["source_bundle_digest"] = ""
    payload["source_provenance"] = []
    payload["source_provenance_digest"] = ""
    for rule in payload["rules"]:
        rule["authority_layer"] = "synthetic"

    from iching.core.bazi_rules.registry import registry_from_data

    with pytest.raises(ValueError, match="cannot contain synthetic"):
        registry_from_data(payload)


@pytest.mark.parametrize(
    ("field_path", "expected_error"),
    [
        (("production_eligible",), "verified production provenance"),
        (
            ("support_locators", 0, "witness_production_allowed"),
            "rights-ineligible witness",
        ),
    ],
)
def test_packaged_registry_rejects_forged_source_eligibility_facts(
    field_path: tuple[str | int, ...],
    expected_error: str,
) -> None:
    package = resources.files("iching.core.bazi_rules")
    payload = json.loads(
        package.joinpath("bundles/zzq-shen-canonical-v1.json").read_text(
            encoding="utf-8"
        )
    )
    target: Any = payload["source_provenance"][0]
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = False
    payload["bundle_digest"] = ""

    from iching.core.bazi_rules.registry import registry_from_data

    with pytest.raises(ValueError, match=expected_error):
        registry_from_data(payload)
