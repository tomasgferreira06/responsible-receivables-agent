"""Static dataset: loading, validation, splits, label isolation and hashes (protocol 8).

The messages are fixed, hand-written files under ``data/dataset/``; nothing here produces text.
Usage: ``uv run --locked python -m responsible_receivables_agent.dataset {check,build}``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "dataset"
PROTOCOL_PATH = ROOT / "docs" / "protocol" / "protocol.json"
PROTOCOL: dict[str, Any] = json.loads(PROTOCOL_PATH.read_text("utf-8"))

DATASET_VERSION = "2.1.0"
# Frozen 2026-10-20 (D18): splits.json is fixed and protected by its hash; it is no longer
# re-derived from the labels, because later label corrections would reshuffle the test set.
FROZEN = True
SPLIT_SEED = 20261019
SPLITS = ("seed_stock", "pool", "validation", "test")
SPLIT_SIZES: dict[str, int] = {s: PROTOCOL["experiment"]["splits"][s] for s in SPLITS}
CLASSES: list[str] = [c["id"] for c in PROTOCOL["classes"]]
CRITICAL: set[str] = set(PROTOCOL["classification_cost"]["critical_classes"])
REASONS: set[str] = {r["id"] for r in PROTOCOL["review_reasons"]}
JACCARD_MAX: float = PROTOCOL["experiment"]["leakage"]["near_duplicate_char5gram_jaccard"]

CASE_FIELDS = (
    "case_id",
    "customer_id",
    "invoice_id",
    "pending_amount_eur",
    "due_date",
    "received_date",
    "message_text",
)
ANNOTATION_FIELDS = ("case_id", "message_label", "needs_additional_review", "review_reasons")
ADJUDICATION_FIELDS = ("case_id", "issue", "decision")
ID_PATTERNS = {"case_id": r"RRA-\d{4}", "customer_id": r"CLI-\d{3}", "invoice_id": r"FT-\d{3,4}"}
FILES = ("cases.jsonl", "annotations.jsonl", "adjudications.jsonl", "splits.json")

Record = dict[str, Any]


def read_jsonl(path: Path) -> list[Record]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_cases(path: Path = DATA_DIR / "cases.jsonl") -> list[Record]:
    return read_jsonl(path)


def load_annotations(path: Path = DATA_DIR / "annotations.jsonl") -> list[Record]:
    return read_jsonl(path)


def load_splits(path: Path = DATA_DIR / "splits.json") -> dict[str, list[str]]:
    data: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return {s: list(data["splits"][s]) for s in SPLITS}


# ---------------------------------------------------------------- label isolation (8.2.5-8.2.6)


def load_inputs(split: str) -> list[Record]:
    """Cases of a split as the classifier and the selector see them: cases.jsonl has no labels."""
    ids = set(load_splits()[split])
    return [c for c in load_cases() if c["case_id"] in ids]


def load_gold(split: str, *, unlock_test: bool = False) -> dict[str, Record]:
    """Reference labels for evaluation code. Pool labels only through ``Oracle``; the test split
    must be unlocked explicitly by the final evaluation."""
    if split == "pool":
        raise PermissionError("pool labels are only available through Oracle.query")
    if split == "test" and not unlock_test:
        raise PermissionError("test labels are sealed; pass unlock_test=True in final evaluation")
    ids = set(load_splits()[split])
    return {a["case_id"]: a for a in load_annotations() if a["case_id"] in ids}


class Oracle:
    """Simulated annotator (8.2.10): answers only for pool ids, and logs every query."""

    def __init__(self) -> None:
        pool = set(load_splits()["pool"])
        self._gold = {a["case_id"]: a for a in load_annotations() if a["case_id"] in pool}
        self.queried: list[str] = []

    def query(self, case_ids: Iterable[str]) -> dict[str, Record]:
        ids = list(case_ids)
        outside = [cid for cid in ids if cid not in self._gold]
        if outside:
            raise PermissionError(f"oracle only answers pool cases: {outside}")
        self.queried.extend(ids)
        return {cid: dict(self._gold[cid]) for cid in ids}


# ---------------------------------------------------------------- validation


def validate_records(
    cases: list[Record], annotations: list[Record], adjudications: Iterable[Record] = ()
) -> list[str]:
    errors: list[str] = []
    invoices: dict[str, tuple[Any, ...]] = {}
    for c in cases:
        cid = c.get("case_id")
        if set(c) != set(CASE_FIELDS):
            errors.append(f"{cid}: case fields {sorted(c)}")
            continue
        for field, pattern in ID_PATTERNS.items():
            if not re.fullmatch(pattern, str(c[field])):
                errors.append(f"{cid}: bad {field} {c[field]!r}")
        amount = c["pending_amount_eur"]
        if not (isinstance(amount, str) and re.fullmatch(r"\d+\.\d{2}", amount)) or not float(
            amount
        ):
            errors.append(f"{cid}: pending_amount_eur must be a positive decimal string")
        try:
            if date.fromisoformat(c["due_date"]) >= date.fromisoformat(c["received_date"]):
                errors.append(f"{cid}: message must be received after the due date")
        except (TypeError, ValueError):
            errors.append(f"{cid}: dates must be ISO YYYY-MM-DD")
        if not isinstance(c["message_text"], str) or not c["message_text"].strip():
            errors.append(f"{cid}: empty message_text")
        invoice = (c["customer_id"], c["pending_amount_eur"], c["due_date"])
        if invoices.setdefault(c["invoice_id"], invoice) != invoice:
            errors.append(f"{cid}: {c['invoice_id']} has different customer/amount/due date")

    for a in annotations:
        cid = a.get("case_id")
        if set(a) != set(ANNOTATION_FIELDS):
            errors.append(f"{cid}: annotation fields {sorted(a)}")
            continue
        reasons = a["review_reasons"]
        if a["message_label"] not in CLASSES:
            errors.append(f"{cid}: unknown message_label {a['message_label']!r}")
        if not isinstance(reasons, list) or not set(reasons) <= REASONS:
            errors.append(f"{cid}: review_reasons outside protocol: {reasons!r}")
        elif reasons != sorted(set(reasons), key=lambda r: int(r[2:])):
            errors.append(f"{cid}: review_reasons must be unique and ordered")
        if a["needs_additional_review"] is not bool(reasons):
            errors.append(f"{cid}: needs_additional_review must equal bool(review_reasons)")

    case_ids = [c.get("case_id") for c in cases]
    if len(set(case_ids)) != len(case_ids):
        errors.append("duplicate case_id in cases.jsonl")
    if sorted(map(str, case_ids)) != sorted(str(a.get("case_id")) for a in annotations):
        errors.append("cases and annotations do not cover the same case_ids")
    for a in adjudications:
        if set(a) != set(ADJUDICATION_FIELDS) or a.get("case_id") not in case_ids:
            errors.append(f"bad adjudication record {a.get('case_id')}")
    texts = Counter(normalize(str(c.get("message_text", ""))) for c in cases)
    errors += [f"exact duplicate message: {t[:60]!r}" for t, n in texts.items() if n > 1]
    return errors


def normalize(text: str) -> str:
    """Lowercase, no accents, no punctuation, digits as 0 (protocol 8.2.3)."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", re.sub(r"\d", "0", text)).split())


def char_ngrams(text: str, n: int = 5) -> frozenset[str]:
    t = normalize(text)
    return frozenset(t[i : i + n] for i in range(max(1, len(t) - n + 1)))


# ---------------------------------------------------------------- splits (8.1-8.2)


def assign_splits(
    cases: list[Record], annotations: list[Record], seed: int = SPLIT_SEED
) -> dict[str, list[str]]:
    """Whole customers go to one split (an invoice belongs to one customer), greedily
    stratified towards the overall profile of class x review (protocol 8.2.1-8.2.2)."""
    label = {
        a["case_id"]: f"{a['message_label']}:{a['needs_additional_review']}" for a in annotations
    }
    share = {c: n / len(label) for c, n in Counter(label.values()).items()}
    groups: dict[str, list[str]] = {}
    for c in cases:
        groups.setdefault(c["customer_id"], []).append(c["case_id"])
    order = sorted(groups)
    random.Random(seed).shuffle(order)
    order.sort(key=lambda g: -len(groups[g]))  # stable: larger customers first, seeded within size
    out: dict[str, list[str]] = {s: [] for s in SPLITS}
    have: dict[str, Counter[str]] = {s: Counter() for s in SPLITS}

    def need(s: str, ids: list[str]) -> float:
        """Class deficit of split s that this customer would fill, relative to the split size."""
        return (
            sum(SPLIT_SIZES[s] * share[label[i]] - have[s][label[i]] for i in ids) / SPLIT_SIZES[s]
        )

    for g in order:
        ids = groups[g]
        fits = [s for s in SPLITS if SPLIT_SIZES[s] - len(out[s]) >= len(ids)]
        if not fits:
            raise ValueError("customer groups do not fit the protocol split sizes")
        target = max(fits, key=lambda s: (need(s, ids), -len(out[s]) / SPLIT_SIZES[s]))
        out[target] += ids
        have[target].update(label[i] for i in ids)
    return {s: sorted(ids) for s, ids in out.items()}


def check_splits(
    cases: list[Record], annotations: list[Record], splits: dict[str, list[str]]
) -> list[str]:
    errors: list[str] = []
    where = {cid: s for s, ids in splits.items() for cid in ids}
    if sum(map(len, splits.values())) != len(where):
        errors.append("a case belongs to more than one split")
    if set(where) != {c["case_id"] for c in cases}:
        errors.append("splits do not cover exactly the dataset cases")
    errors += [
        f"{s}: {len(splits[s])} cases, protocol requires {n}"
        for s, n in SPLIT_SIZES.items()
        if len(splits[s]) != n
    ]
    for key in ("customer_id", "invoice_id"):
        seen: dict[str, set[str]] = {}
        for c in cases:
            seen.setdefault(c[key], set()).add(where.get(c["case_id"], "?"))
        errors += [f"{key} {k} crosses splits {sorted(v)}" for k, v in seen.items() if len(v) > 1]
    if not FROZEN and splits != assign_splits(cases, annotations):
        errors.append(f"splits.json is not reproducible with seed {SPLIT_SEED}")

    grams = [(c["case_id"], where.get(c["case_id"]), char_ngrams(c["message_text"])) for c in cases]
    for i, (a, sa, ga) in enumerate(grams):
        for b, sb, gb in grams[i + 1 :]:
            if sa != sb and len(ga & gb) / len(ga | gb) >= JACCARD_MAX:
                errors.append(f"near-duplicate across splits: {a} ({sa}) / {b} ({sb})")

    exp = PROTOCOL["experiment"]["splits"]
    test = Counter(a["message_label"] for a in annotations if where.get(a["case_id"]) == "test")
    errors += [
        f"test has {test[c]} {c}, minimum {exp['test_min_per_class']}"
        for c in CLASSES
        if test[c] < exp["test_min_per_class"]
    ]
    if sum(test[c] for c in CRITICAL) < exp["test_min_critical_class_items"]:
        errors.append("test has too few critical-class items")
    return errors


# ---------------------------------------------------------------- manifest and hashes (8.2.9)


def sha256_file(path: Path) -> str:
    # LF-normalised so a Git CRLF checkout on Windows gives the same hash.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_manifest(annotations: list[Record], splits: dict[str, list[str]]) -> Record:
    gold = {a["case_id"]: a for a in annotations}
    counts = {
        s: {
            "cases": len(ids),
            "message_label": dict(sorted(Counter(gold[i]["message_label"] for i in ids).items())),
            "needs_additional_review": sum(gold[i]["needs_additional_review"] for i in ids),
        }
        for s, ids in splits.items()
    }
    return {
        "dataset_version": DATASET_VERSION,
        "protocol_version": PROTOCOL["protocol_version"],
        "status": (
            "frozen 2026-10-20 (D18): AI-written, rule-checked, AI-audited; "
            "selected cases decided by the project owner"
        ),
        "human_validation": "partial: owner adjudication of selected cases; no double annotation",
        "test_frozen": FROZEN,
        "split_seed": SPLIT_SEED,
        "split_unit": "customer_id",
        "files_sha256": {f: sha256_file(DATA_DIR / f) for f in FILES},
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "counts": counts,
    }


def check_all() -> list[str]:
    cases, annotations = load_cases(), load_annotations()
    errors = validate_records(cases, annotations, read_jsonl(DATA_DIR / "adjudications.jsonl"))
    if errors:
        return errors
    errors = check_splits(cases, annotations, load_splits())
    manifest = json.loads((DATA_DIR / "manifest.json").read_text("utf-8"))
    if manifest != build_manifest(annotations, load_splits()):
        errors.append("manifest.json is out of date (hashes, versions or counts)")
    return errors


def write_json(path: Path, data: Record) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m responsible_receivables_agent.dataset")
    parser.add_argument(
        "command", choices=["check", "build"], help="build: new dataset version only"
    )
    args = parser.parse_args(argv)
    if args.command == "build":
        if FROZEN:
            splits = load_splits()  # never re-split a frozen dataset; only refresh the manifest
        else:
            splits = assign_splits(load_cases(), load_annotations())
            write_json(DATA_DIR / "splits.json", {"seed": SPLIT_SEED, "splits": splits})
        write_json(DATA_DIR / "manifest.json", build_manifest(load_annotations(), splits))
    errors = check_all()
    for e in errors:
        print(f"ERROR {e}")
    manifest = json.loads((DATA_DIR / "manifest.json").read_text("utf-8"))
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=1))
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
