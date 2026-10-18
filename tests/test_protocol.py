"""Integrity checks for the T02 research protocol artefacts (offline, no LLM calls)."""

import json
import math
from pathlib import Path
from typing import Any

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
PROTOCOL: dict[str, Any] = json.loads((DOCS / "protocol" / "protocol.json").read_text("utf-8"))
EXAMPLES: list[dict[str, Any]] = json.loads(
    (DOCS / "protocol" / "reference_examples.json").read_text("utf-8")
)["examples"]
# Backticks are stripped so markdown tables can be compared with the JSON values.
PROTOCOL_MD = (DOCS / "EXPERIMENT_PROTOCOL.md").read_text("utf-8").replace("`", "")
DECISIONS_MD = (DOCS / "DECISIONS.md").read_text("utf-8")

CLASSES: list[str] = [c["id"] for c in PROTOCOL["classes"]]
COST: dict[str, Any] = PROTOCOL["classification_cost"]
MATRIX: list[list[float]] = COST["values"]
OTHER = "OTHER_OR_UNCLEAR"
POLICY: dict[str, Any] = PROTOCOL["action_policy"]
REASON_IDS: set[str] = {r["id"] for r in PROTOCOL["review_reasons"]}
FLAGS: dict[str, str | None] = PROTOCOL["risk_flags"]
PRIORITY: dict[str, int] = {c["id"]: c["priority"] for c in PROTOCOL["classes"]}


def derive_policy(flags: list[str]) -> str:
    for rule in POLICY["mapping_first_match"]:
        if rule.get("default") or set(rule["if_any_flag"]) & set(flags):
            return str(rule["profile"])
    raise AssertionError("mapping has no default")


def test_taxonomy_has_five_classes_with_unique_priorities() -> None:
    assert len(CLASSES) == 5
    assert COST["order"] == [
        "PAYMENT_PROMISE",
        "PAYMENT_CLAIM",
        "PAYMENT_PLAN_REQUEST",
        "INVOICE_DISPUTE",
        OTHER,
    ]
    assert set(COST["order"]) == set(CLASSES)
    assert sorted(PRIORITY.values()) == [1, 2, 3, 4, 5]
    by_priority = sorted((c for c in CLASSES if c != OTHER), key=PRIORITY.__getitem__)
    assert PROTOCOL["multi_intent_priority"] == by_priority
    assert PRIORITY[OTHER] == 5


def test_cost_matrix_is_valid() -> None:
    assert len(MATRIX) == 5 and all(len(row) == 5 for row in MATRIX)
    top = COST["scale"]["max"]
    for i, row in enumerate(MATRIX):
        assert row[i] == 0
        for j, v in enumerate(row):
            assert math.isfinite(v) and 0 <= v <= top
            if i != j:
                assert v > 0, "off-diagonal errors must have a positive cost"


def test_cost_matrix_is_asymmetric_where_justified() -> None:
    idx = {c: i for i, c in enumerate(COST["order"])}
    dispute, promise = idx["INVOICE_DISPUTE"], idx["PAYMENT_PROMISE"]
    assert MATRIX[dispute][promise] > MATRIX[promise][dispute]


def test_critical_classes_are_derived_from_matrix() -> None:
    threshold = COST["critical_class_rule"]["min_max_row_cost"]
    derived = {c for c, row in zip(COST["order"], MATRIX, strict=True) if max(row) >= threshold}
    assert derived == set(COST["critical_classes"])


def test_markdown_matrix_matches_json() -> None:
    for name, row in zip(COST["order"], MATRIX, strict=True):
        line = f"| {name} | " + " | ".join(str(int(v)) for v in row) + " |"
        assert line in PROTOCOL_MD, f"matrix row not in protocol: {line}"


def test_routing_costs() -> None:
    routing = PROTOCOL["routing_cost"]
    fn = routing["false_negative_by_gold_class"]
    assert set(fn) == set(CLASSES)
    assert routing["true_positive"] == 0 and routing["true_negative"] == 0
    assert 0 < routing["false_positive"] < min(fn.values())
    assert all(math.isfinite(v) for v in fn.values())


def test_action_policy_invariants() -> None:
    assert POLICY["always_true"]["external_communication_requires_human_approval"] is True
    assert POLICY["always_true"]["may_modify_accounting_data"] is False
    assert POLICY["always_true"]["may_confirm_payment_from_client_statement"] is False
    forbidden = set(POLICY["always_forbidden"])
    assert {"confirm_payment", "modify_accounting_data", "send_external_without_approval"} <= (
        forbidden
    )
    for profile in POLICY["profiles"].values():
        assert set(profile["allowed"]) <= set(POLICY["tools"])
        assert not set(profile["allowed"]) & forbidden
    profiles = {rule["profile"] for rule in POLICY["mapping_first_match"]}
    assert profiles == set(POLICY["profiles"])
    assert POLICY["mapping_first_match"][-1].get("default") is True
    mapped = {f for rule in POLICY["mapping_first_match"] for f in rule.get("if_any_flag", [])}
    assert mapped == set(FLAGS)


def test_review_reasons_and_flags_are_consistent() -> None:
    assert len(REASON_IDS) == len(PROTOCOL["review_reasons"]) == 8
    assert {r for r in FLAGS.values() if r} <= REASON_IDS
    mandatory = {r["id"] for r in PROTOCOL["review_reasons"] if r["mandatory_rule"]}
    assert mandatory == {"RV5", "RV6", "RV7"}


def test_experiment_parameters_are_coherent() -> None:
    exp = PROTOCOL["experiment"]
    splits = exp["splits"]
    assert splits["initial_memory_n0"] <= splits["seed_stock"]
    assert 100 <= splits["test"] <= 150
    assert 20 <= splits["initial_memory_n0"] <= 30
    assert splits["test_min_per_class"] * 5 <= splits["test"]
    assert exp["annotation_budget"] == 40
    assert exp["eval_points"][0] == 0
    assert exp["eval_points"][-1] == exp["annotation_budget"]
    assert exp["annotation_budget"] % exp["round_size"] == 0
    assert exp["eval_points"] == list(range(0, 41, exp["round_size"]))
    assert set(exp["e2"]["s2_memory_sources"]) <= set(exp["strategies"])
    ablations = exp["risk_aware"]["ablations"]
    assert len({tuple(a) for a in ablations}) == 7
    assert all(set(a) <= {"U", "R", "D"} and a for a in ablations)
    assert exp["llm_calls"]["votes_n"] >= exp["risk_aware"]["min_valid_votes"]
    stats = exp["statistics"]
    assert stats["multiplicity"] == "holm" and stats["ci_multiplicity_adjusted"] is False
    assert "inversão de sinal" in PROTOCOL_MD and "não ajustados" in PROTOCOL_MD
    assert "sem correção +1" in PROTOCOL_MD and "com correção +1" in PROTOCOL_MD


def test_documents_reference_every_protocol_identifier() -> None:
    names = (
        CLASSES
        + sorted(REASON_IDS)
        + list(POLICY["profiles"])
        + list(FLAGS)
        + list(PROTOCOL["experiment"]["strategies"])
        + ["S0", "S1", "S2"]
    )
    missing = [n for n in names if n not in PROTOCOL_MD]
    assert not missing, f"not documented in EXPERIMENT_PROTOCOL.md: {missing}"
    decisions = [f"D{i:02d}" for i in range(1, 16)]
    assert [d for d in decisions if f"## {d} " not in DECISIONS_MD] == []


def test_reference_examples_cover_the_required_scenarios() -> None:
    assert len(EXAMPLES) >= 10
    assert len({e["id"] for e in EXAMPLES}) == len(EXAMPLES)
    assert {e["message_label"] for e in EXAMPLES} == set(CLASSES)
    assert {e["action_policy"] for e in EXAMPLES} == set(POLICY["profiles"])
    assert {f for e in EXAMPLES for f in e["risk_flags"]} == set(FLAGS)


@pytest.mark.parametrize("ex", EXAMPLES, ids=[e["id"] for e in EXAMPLES])
def test_reference_example_follows_the_rules(ex: dict[str, Any]) -> None:
    label: str = ex["message_label"]
    secondary: list[str] = ex["secondary_intents"]
    flags: list[str] = ex["risk_flags"]
    reasons: list[str] = ex["review_reasons"]
    ctx: dict[str, Any] = ex["context"]

    assert label in CLASSES
    assert OTHER not in secondary and label not in secondary
    assert all(s in CLASSES for s in secondary)
    if label == OTHER:
        # Secondary intents only exist when a contradiction forced OTHER_OR_UNCLEAR.
        assert (not secondary) or "contradictory_statements" in flags
    else:
        assert all(PRIORITY[label] < PRIORITY[s] for s in secondary)
        assert "contradictory_statements" not in flags

    assert set(flags) <= set(FLAGS)
    assert set(reasons) <= REASON_IDS
    for flag, reason in FLAGS.items():
        if reason:
            assert (flag in flags) == (reason in reasons)
    assert ex["needs_additional_review"] is bool(reasons)
    assert ex["action_policy"] == derive_policy(flags)
    profile = POLICY["profiles"][ex["action_policy"]]
    assert (not profile["mandatory_review"]) or ex["needs_additional_review"]

    assert ("RV1" in reasons) == ("INVOICE_DISPUTE" in [label, *secondary])
    th = PROTOCOL["review_thresholds"]
    if (
        label == "PAYMENT_PLAN_REQUEST"
        and ctx["pending_amount_eur"] >= th["high_value_pending_eur"]
    ):
        assert "RV3" in reasons
    if (
        label in ("PAYMENT_PROMISE", "PAYMENT_PLAN_REQUEST")
        and ctx["broken_promises_count"] >= th["broken_promises_for_rv4"]
    ):
        assert "RV4" in reasons
    assert "RV4" not in reasons or ctx["broken_promises_count"] >= th["broken_promises_for_rv4"]
