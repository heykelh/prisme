"""Le referentiel est une donnee critique : il merite ses propres tests."""

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "requirements_v1.json"

VALID_CATEGORIES = {
    "risk_management",
    "data_governance",
    "documentation",
    "logging",
    "transparency",
    "human_oversight",
    "robustness",
}

EXPECTED_ARTICLES = {f"Article {n}" for n in range(9, 16)}


def load():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_file_is_valid_json_with_requirements():
    payload = load()
    assert payload["version"] >= 1
    assert len(payload["requirements"]) >= 30


def test_criterion_codes_are_unique():
    payload = load()
    codes = [r["criterion_code"] for r in payload["requirements"]]
    assert len(codes) == len(set(codes))


def test_all_articles_9_to_15_covered():
    payload = load()
    articles = {r["article"] for r in payload["requirements"]}
    assert articles == EXPECTED_ARTICLES


def test_categories_are_valid():
    payload = load()
    for r in payload["requirements"]:
        assert r["category"] in VALID_CATEGORIES, r["criterion_code"]


def test_criterion_texts_are_substantive():
    payload = load()
    for r in payload["requirements"]:
        assert len(r["criterion_text"]) >= 40, r["criterion_code"]
