"""Checks for the static dataset (T03). Offline; no LLM calls.

Passing these tests means the files are internally consistent with the protocol rules. It is not
human validation of the labels (T04).
"""

import copy
from collections import Counter
from typing import Any

import pytest

from responsible_receivables_agent import dataset as ds

CASES = ds.load_cases()
ANNOTATIONS = ds.load_annotations()
SPLITS = ds.load_splits()
GOLD = {a["case_id"]: a for a in ANNOTATIONS}
MANDATORY = {"RV5", "RV6", "RV7"}


def test_dataset_files_pass_every_check() -> None:
    assert ds.check_all() == []


def test_schemas_are_minimal() -> None:
    assert all(tuple(c) == ds.CASE_FIELDS for c in CASES)
    assert all(tuple(a) == ds.ANNOTATION_FIELDS for a in ANNOTATIONS)
    assert len(CASES) == len(ANNOTATIONS) == sum(ds.SPLIT_SIZES.values()) == 510


def test_rv4_is_gone_and_review_follows_reasons() -> None:
    assert all("RV4" not in a["review_reasons"] for a in ANNOTATIONS)
    assert all(a["needs_additional_review"] is bool(a["review_reasons"]) for a in ANNOTATIONS)


def test_review_is_not_a_function_of_the_class() -> None:
    """E2 must not be solvable from message_label alone, also outside the mandatory rules."""
    for split in ("pool", "test"):
        gold = [GOLD[i] for i in SPLITS[split]]
        for label in ("PAYMENT_CLAIM", "PAYMENT_PLAN_REQUEST", "OTHER_OR_UNCLEAR"):
            assert {a["needs_additional_review"] for a in gold if a["message_label"] == label} == {
                True,
                False,
            }
        discretionary = [a for a in gold if not MANDATORY & set(a["review_reasons"])]
        positives = Counter(a["message_label"] for a in discretionary if a["review_reasons"])
        assert len(positives) >= 4  # discretionary review cases in at least four classes


def test_inputs_carry_no_labels() -> None:
    for split in ds.SPLITS:
        rows = ds.load_inputs(split)
        assert len(rows) == ds.SPLIT_SIZES[split]
        assert all(set(r) == set(ds.CASE_FIELDS) for r in rows)


def test_gold_access_is_restricted() -> None:
    with pytest.raises(PermissionError):
        ds.load_gold("pool")
    with pytest.raises(PermissionError):
        ds.load_gold("test")
    assert set(ds.load_gold("validation")) == set(SPLITS["validation"])
    assert set(ds.load_gold("test", unlock_test=True)) == set(SPLITS["test"])


def test_oracle_answers_only_queried_pool_cases() -> None:
    oracle = ds.Oracle()
    picked = SPLITS["pool"][:3]
    answer = oracle.query(picked)
    assert set(answer) == set(picked) and oracle.queried == picked
    assert answer[picked[0]] == GOLD[picked[0]]
    for other in ("seed_stock", "validation", "test"):
        with pytest.raises(PermissionError):
            oracle.query([SPLITS[other][0]])
    assert oracle.queried == picked


def test_splits_are_frozen_or_reproducible_and_group_customers() -> None:
    if not ds.FROZEN:
        assert ds.assign_splits(CASES, ANNOTATIONS) == SPLITS
    assert ds.assign_splits(CASES, ANNOTATIONS) == ds.assign_splits(CASES, ANNOTATIONS)
    assert ds.assign_splits(CASES, ANNOTATIONS, seed=1) != SPLITS
    where = {cid: s for s, ids in SPLITS.items() for cid in ids}
    for key in ("customer_id", "invoice_id"):
        groups: dict[str, set[str]] = {}
        for c in CASES:
            groups.setdefault(c[key], set()).add(where[c["case_id"]])
        assert all(len(v) == 1 for v in groups.values())


def _errors(cases: list[dict[str, Any]], annotations: list[dict[str, Any]]) -> list[str]:
    return ds.validate_records(cases, annotations) or ds.check_splits(cases, annotations, SPLITS)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c, a: a[0]["review_reasons"].append("RV4"),
        lambda c, a: a[1].update(needs_additional_review=True),
        lambda c, a: c[0].update(broken_promises_count=0),
        lambda c, a: a[0].update(secondary_intents=[]),
        lambda c, a: c[0].update(pending_amount_eur=12.5),
        lambda c, a: c[0].update(received_date=c[0]["due_date"]),
        lambda c, a: c[1].update(message_text=c[0]["message_text"]),
        lambda c, a: a.pop(),
    ],
    ids=[
        "rv4",
        "review-mismatch",
        "old-case-field",
        "old-annotation-field",
        "float-amount",
        "dates",
        "exact-duplicate",
        "missing-annotation",
    ],
)
def test_validation_rejects_broken_records(mutate: Any) -> None:
    cases, annotations = copy.deepcopy(CASES), copy.deepcopy(ANNOTATIONS)
    mutate(cases, annotations)
    assert ds.validate_records(cases, annotations)


def test_leakage_checks_catch_cross_split_customers_and_near_duplicates() -> None:
    by_id = {c["case_id"]: c for c in copy.deepcopy(CASES)}
    test_case, pool_case = by_id[SPLITS["test"][0]], by_id[SPLITS["pool"][0]]
    test_case["customer_id"] = pool_case["customer_id"]
    errors = _errors(list(by_id.values()), ANNOTATIONS)
    assert any("customer_id" in e and "crosses splits" in e for e in errors)

    by_id = {c["case_id"]: c for c in copy.deepcopy(CASES)}
    by_id[SPLITS["test"][0]]["message_text"] = by_id[SPLITS["pool"][0]]["message_text"] + " Obg."
    errors = _errors(list(by_id.values()), ANNOTATIONS)
    assert any("near-duplicate across splits" in e for e in errors)
