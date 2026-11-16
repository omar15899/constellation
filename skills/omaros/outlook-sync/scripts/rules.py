from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from config import TAXONOMY_PATH


@dataclass
class Category:
    id: str
    description: str
    color: str | None
    target_folder: str | None
    rules: dict[str, Any] = field(default_factory=dict)


@dataclass
class Taxonomy:
    version: int
    categories: list[Category]
    junk_category: str
    rescue_from_junk: bool

    @classmethod
    def load(cls, path: Path = TAXONOMY_PATH) -> "Taxonomy":
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        categories = [
            Category(
                id=str(entry.get("id", "")),
                description=str(entry.get("description", "")),
                color=entry.get("color"),
                target_folder=entry.get("target_folder"),
                rules=dict(entry.get("rules") or {}),
            )
            for entry in (data.get("categories") or [])
        ]
        return cls(
            version=int(data.get("version", 1)),
            categories=categories,
            junk_category=str(data.get("junk_category", "Junk")),
            rescue_from_junk=bool(data.get("rescue_from_junk", True)),
        )

    def category_ids(self) -> list[str]:
        return [c.id for c in self.categories]

    def get(self, cid: str) -> Category | None:
        for c in self.categories:
            if c.id == cid:
                return c
        return None


@dataclass
class RuleResult:
    category: str | None
    confidence: float
    reason: str


class RuleClassifier:
    def __init__(self, taxonomy: Taxonomy) -> None:
        self.taxonomy = taxonomy

    def classify(self, features: dict[str, Any]) -> RuleResult:
        from_address = str(features.get("from_address", "")).lower()
        subject = str(features.get("subject", "")).lower()
        has_list_unsubscribe = bool(features.get("has_list_unsubscribe", False))

        for category in self.taxonomy.categories:
            rules = category.rules or {}

            from_domains = [str(d).lower() for d in (rules.get("from_domains") or [])]
            if from_address and any(from_address.endswith(domain) for domain in from_domains):
                return RuleResult(
                    category.id,
                    0.95,
                    f"from_address matches domain rule for {category.id}",
                )

            from_addresses = [str(a).lower() for a in (rules.get("from_addresses") or [])]
            if from_address and from_address in from_addresses:
                return RuleResult(
                    category.id,
                    0.95,
                    f"from_address exact match for {category.id}",
                )

            subject_keywords = [str(k).lower() for k in (rules.get("subject_keywords") or [])]
            if subject and any(kw in subject for kw in subject_keywords):
                return RuleResult(
                    category.id,
                    0.95,
                    f"subject keyword match for {category.id}",
                )

            if rules.get("header_list_unsubscribe") and has_list_unsubscribe:
                return RuleResult(
                    category.id,
                    0.95,
                    f"List-Unsubscribe header matches {category.id}",
                )

        return RuleResult(None, 0.0, "no deterministic rule matched")
