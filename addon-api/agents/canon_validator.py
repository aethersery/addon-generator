"""
Canon Validator Agent - Cross-references lore against canonical sources.

Validates facts, flags contradictions, assigns canon confidence scores,
and provides chapter/page citations for verification.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from core.state import VersionedAddonState, LoreData, GenerationStatus
from core.versioned_state import UserFeedback, FeedbackType
from routers.llm_router import get_router, TaskType, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class CanonFact:
    """A single verified or disputed fact."""
    claim: str
    domain: str
    canon_status: str  # "confirmed", "contradicted", "unverified", "fanon"
    confidence: float  # 0.0 - 1.0
    sources: list[dict] = field(default_factory=list)  # {"source": "...", "location": "Ch. 234", "quote": "..."}
    contradictions: list[str] = field(default_factory=list)
    minecraft_implication: str = ""


@dataclass
class ValidationReport:
    """Complete validation report for a lore dataset."""
    total_facts: int = 0
    confirmed: int = 0
    contradicted: int = 0
    unverified: int = 0
    fanon: int = 0
    facts: list[CanonFact] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class CanonValidator:
    """
    Validates lore research against canonical sources.
    Provides citation-backed verification for every claim.
    """

    def __init__(self):
        self.router = get_router()
        self.canon_hierarchy = [
            "official_novel",      # Original source material
            "official_anime",      # Official adaptation
            "official_manga",      # Official manga
            "official_game",       # Official game
            "author_statement",    # Word of God (interviews, Q&As)
            "official_wiki",       # Curated official wiki
            "fandom_wiki",         # Community wiki (Fandom)
            "reddit_discussion",   # Community discussion
            "fan_theory",          # Unverified speculation
        ]

    async def validate(self, state: VersionedAddonState) -> VersionedAddonState:
        """Validate all lore in the current version."""
        current = state.get_current_version()
        if not current or not current.lore:
            state.add_log("No lore to validate")
            return state

        state.set_status(GenerationStatus.RESEARCHING, "canon_validator",
                        "Validating lore against canonical sources...")
        state.add_log("Starting canon validation...")

        # Extract all claims from lore
        claims = self._extract_claims(current.lore, current.lore.references or [])
        state.add_log(f"Extracted {len(claims)} claims for validation")

        # Validate each claim
        validated_facts = await self._validate_claims(state.theme, claims)

        # Build validation report
        report = self._build_report(validated_facts)

        # Store in version
        current.lore.references = current.lore.references or []
        current.lore.references.append({
            "type": "canon_validation",
            "data": {
                "report": {
                    "total_facts": report.total_facts,
                    "confirmed": report.confirmed,
                    "contradicted": report.contradicted,
                    "unverified": report.unverified,
                    "fanon": report.fanon,
                    "critical_issues": report.critical_issues,
                    "recommendations": report.recommendations,
                },
                "facts": [
                    {
                        "claim": f.claim,
                        "domain": f.domain,
                        "canon_status": f.canon_status,
                        "confidence": f.confidence,
                        "sources": f.sources,
                        "contradictions": f.contradictions,
                        "minecraft_implication": f.minecraft_implication,
                    }
                    for f in report.facts
                ],
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Generate feedback for contradicted facts
        for fact in validated_facts:
            if fact.canon_status == "contradicted" and fact.confidence > 0.7:
                feedback = UserFeedback(
                    version=state.current_version,
                    feedback_type=FeedbackType.CANON_CORRECTION,
                    title=f"Canon contradiction: {fact.claim[:80]}",
                    description=f"Research claims '{fact.claim}' but canon sources indicate otherwise.",
                    canon_reference=", ".join([s.get("location", "") for s in fact.sources]),
                    affected_assets=[fact.domain],
                    suggested_fix=f"Update to match canon: {fact.contradictions[0] if fact.contradictions else 'See sources'}",
                    priority=2,
                )
                state.add_feedback(feedback)

        state.set_status(GenerationStatus.RESEARCHING, "canon_validator",
                        f"Validation complete: {report.confirmed}/{report.total_facts} confirmed")
        state.add_log(f"Canon validation: {report.confirmed} confirmed, {report.contradicted} contradicted, {report.unverified} unverified")

        return state

    def _extract_claims(self, lore: LoreData, domain_refs: list[dict]) -> list[dict]:
        """Extract verifiable claims from lore and domain research."""
        claims = []

        # From entities
        for e in lore.entities:
            claims.append({
                "claim": f"Entity '{e.display_name}' exists with abilities: {', '.join(e.abilities)}",
                "domain": "entities",
                "source_ref": e.name,
                "type": "entity",
            })

        # From items
        for i in lore.items:
            claims.append({
                "claim": f"Item '{i.display_name}' is a {i.item_type} with rarity {i.rarity}",
                "domain": "items",
                "source_ref": i.name,
                "type": "item",
            })

        # From mechanics
        for m in lore.mechanics:
            claims.append({
                "claim": f"Mechanic '{m.name}': {m.description}",
                "domain": "mechanics",
                "source_ref": m.name,
                "type": "mechanic",
            })

        # From domain research references
        for ref in domain_refs:
            if isinstance(ref, dict) and "domain" in ref:
                domain = ref["domain"]
                mc_notes = ref.get("minecraft_notes", [])
                for note in mc_notes:
                    claims.append({
                        "claim": note,
                        "domain": domain,
                        "source_ref": domain,
                        "type": "minecraft_mapping",
                    })

        return claims

    async def _validate_claims(self, theme: str, claims: list[dict]) -> list[CanonFact]:
        """Validate claims using LLM with canon hierarchy awareness."""
        validated = []

        # Process in batches
        batch_size = 10
        for i in range(0, len(claims), batch_size):
            batch = claims[i:i+batch_size]
            batch_facts = await self._validate_batch(theme, batch)
            validated.extend(batch_facts)

        return validated

    async def _validate_batch(self, theme: str, claims: list[dict]) -> list[CanonFact]:
        """Validate a batch of claims."""
        claims_text = "\n".join([
            f"{j+1}. [{c['domain']}] {c['claim']} (ref: {c['source_ref']})"
            for j, c in enumerate(claims)
        ])

        prompt = f"""You are a canon fact-checker for **{theme}**.
Validate each claim against the canon hierarchy:
1. Official novel/light novel (highest)
2. Official anime/manga adaptation
3. Author statements (interviews, Q&As)
4. Official wiki / curated sources
5. Fandom wiki (community)
6. Reddit/discussion (speculation)
7. Fan theory (lowest)

**Claims to validate:**
{claims_text}

**For each claim, output JSON:**
```json
[
  {{
    "claim_index": 0,
    "canon_status": "confirmed|contradicted|unverified|fanon",
    "confidence": 0.0-1.0,
    "sources": [
      {{"source": "Source name", "type": "official_novel|official_anime|author_statement|...", "location": "Chapter 234 / Episode 12 / Interview 2023", "quote": "Exact quote"}}
    ],
    "contradictions": ["What canon actually says if different"],
    "minecraft_implication": "How this affects Minecraft implementation"
  }}
]
```"""

        try:
            response = await self.router.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                task_type=TaskType.REASONING,
                temperature=0.1,
                max_tokens=8000,
            )
            results = json.loads(self._extract_json(response.content))

            for r in results:
                idx = r.get("claim_index", 0)
                if idx < len(claims):
                    c = claims[idx]
                    validated.append(CanonFact(
                        claim=c["claim"],
                        domain=c["domain"],
                        canon_status=r.get("canon_status", "unverified"),
                        confidence=r.get("confidence", 0.5),
                        sources=r.get("sources", []),
                        contradictions=r.get("contradictions", []),
                        minecraft_implication=r.get("minecraft_implication", ""),
                    ))

        except Exception as e:
            logger.error(f"Batch validation failed: {e}")
            # Fallback: mark all as unverified
            for c in claims:
                validated.append(CanonFact(
                    claim=c["claim"],
                    domain=c["domain"],
                    canon_status="unverified",
                    confidence=0.3,
                    sources=[],
                    contradictions=[],
                    minecraft_implication="",
                ))

        return validated

    def _build_report(self, facts: list[CanonFact]) -> ValidationReport:
        """Build validation summary report."""
        report = ValidationReport(total_facts=len(facts))
        for f in facts:
            report.facts.append(f)
            if f.canon_status == "confirmed":
                report.confirmed += 1
            elif f.canon_status == "contradicted":
                report.contradicted += 1
            elif f.canon_status == "fanon":
                report.fanon += 1
            else:
                report.unverified += 1

            if f.canon_status == "contradicted" and f.confidence > 0.8:
                report.critical_issues.append(
                    f"HIGH CONFIDENCE CONTRADICTION in {f.domain}: {f.claim[:100]}"
                )

        # Recommendations
        if report.contradicted > 0:
            report.recommendations.append(
                f"Review {report.contradicted} contradicted claims before generation"
            )
        if report.unverified > report.total_facts * 0.3:
            report.recommendations.append(
                "High unverified ratio - consider additional research sources"
            )
        if report.fanon > 0:
            report.recommendations.append(
                f"{report.fanon} fanon claims detected - mark clearly in addon documentation"
            )

        return report

    def _extract_json(self, content: str) -> str:
        content = content.strip()
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            return content[start:end].strip()
        return content


# Convenience function
async def validate_lore(state: VersionedAddonState) -> VersionedAddonState:
    """Standalone validation function."""
    validator = CanonValidator()
    return await validator.validate(state)
