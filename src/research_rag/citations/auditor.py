"""Citation auditor for verifying LLM claims against source chunks."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class CitationAuditor:
    """Audits whether LLM claims are supported by cited source chunks.

    Extracts claims around [N] citation markers at multiple granularities
    and checks them against source chunk text via substring containment.
    """

    def extract_claims(self, text: str, citation_number: int) -> list[str]:
        """Extract claims around a [N] citation marker at 3 granularities.

        Args:
            text: Full answer text containing [N] markers.
            citation_number: The citation number N to look for.

        Returns:
            List of [sentence, last_50_chars, last_20_chars]
            with any empty entries excluded.
        """
        marker = f"[{citation_number}]"
        pos = text.find(marker)
        if pos == -1:
            return []

        # Text occurring strictly before the [N] marker
        before = text[:pos]

        claims = []

        # --- (a) Full sentence containing the marker ---
        # Start from the last period-space or period before the marker,
        # or from the beginning of text if no period is found.
        last_period = before.rfind(". ")
        if last_period == -1:
            last_period = before.rfind(".")
        if last_period == -1:
            sentence = before
        else:
            sentence = before[last_period + 1:]  # skip the period delimiter

        sentence = sentence.strip()
        sentence = re.sub(r'\[\d+\]', '', sentence).strip()
        if sentence:
            claims.append(sentence)

        # --- (b) Last 50 characters before [N] ---
        last_50 = before[-50:] if len(before) >= 50 else before
        last_50 = last_50.strip()
        last_50 = re.sub(r'\[\d+\]', '', last_50).strip()
        if last_50:
            claims.append(last_50)

        # --- (c) Last 20 characters before [N] ---
        last_20 = before[-20:] if len(before) >= 20 else before
        last_20 = last_20.strip()
        last_20 = re.sub(r'\[\d+\]', '', last_20).strip()
        if last_20:
            claims.append(last_20)

        return claims

    def verify_claim(self, claim: str, chunk_text: str) -> bool:
        """Verify a claim by substring containment against chunk text.

        Both strings are normalised (lowercased, stripped, whitespace
        collapsed) before the containment check.

        Args:
            claim: The extracted claim text.
            chunk_text: Full text of the source chunk.

        Returns:
            True if the normalised claim is found inside the normalised
            chunk text (simple substring match).
        """
        def _normalise(s: str) -> str:
            return ' '.join(s.lower().split())

        return _normalise(claim) in _normalise(chunk_text)

    def audit(
        self,
        answer: str,
        citations: list[dict],
        results: Optional[list],
    ) -> dict:
        """Audit all citations in an answer against source chunks.

        For each citation the method extracts claims around the
        corresponding ``[N]`` marker in the answer text and checks
        whether any of those claims appear in the referenced chunk.

        Edge cases:
        - No ``[N]`` marker in answer → skip (verified=True).
        - ``results`` is ``None``/empty → skip all (verified=True).
        - Empty / all-whitespace claim after extraction → skip (verified=True).

        Args:
            answer: The LLM-generated answer containing ``[N]`` markers.
            citations: List of dicts, each with at least ``citation_number``
                and optionally ``chunk_id``.
            results: List of ``SearchResult`` objects from the retriever,
                each exposing a ``.text`` attribute. Indexed by
                ``citation_number - 1``.

        Returns:
            Dict with shape::

                {
                    "total_citations": int,
                    "verified_count": int,
                    "flagged_count": int,
                    "details": [
                        {
                            "citation_number": int,
                            "verified": bool,
                            "flagged_text": str | None,
                            "chunk_id": str,
                        },
                        ...
                    ],
                }
        """
        # --- Short-circuit: nothing to check against ---
        if not results:
            return {
                "total_citations": len(citations),
                "verified_count": len(citations),
                "flagged_count": 0,
                "details": [
                    {
                        "citation_number": c.get("citation_number", i + 1),
                        "verified": True,
                        "flagged_text": None,
                        "chunk_id": c.get("chunk_id", ""),
                    }
                    for i, c in enumerate(citations)
                ],
            }

        details: list[dict] = []
        verified_count = 0
        flagged_count = 0

        for citation in citations:
            citation_number = citation.get("citation_number", 0)
            chunk_id = citation.get("chunk_id", "")

            # --- Edge: marker absent from answer ---
            if not re.search(rf"\[{citation_number}[^\]]*\]", answer):
                details.append({
                    "citation_number": citation_number,
                    "verified": True,
                    "flagged_text": None,
                    "chunk_id": chunk_id,
                })
                verified_count += 1
                continue

            # --- Edge: out-of-range index in results ---
            idx = citation_number - 1
            if idx < 0 or idx >= len(results):
                details.append({
                    "citation_number": citation_number,
                    "verified": True,
                    "flagged_text": None,
                    "chunk_id": chunk_id,
                })
                verified_count += 1
                continue

            chunk_text = getattr(results[idx], "text", None)
            if not chunk_text:
                # No text attribute or empty string
                details.append({
                    "citation_number": citation_number,
                    "verified": True,
                    "flagged_text": None,
                    "chunk_id": chunk_id,
                })
                verified_count += 1
                continue

            # --- Extract and verify claims ---
            claims = self.extract_claims(answer, citation_number)

            if not claims:
                # No usable claims extracted
                details.append({
                    "citation_number": citation_number,
                    "verified": True,
                    "flagged_text": None,
                    "chunk_id": chunk_id,
                })
                verified_count += 1
                continue

            matched = any(self.verify_claim(c, chunk_text) for c in claims)

            if matched:
                details.append({
                    "citation_number": citation_number,
                    "verified": True,
                    "flagged_text": None,
                    "chunk_id": chunk_id,
                })
                verified_count += 1
            else:
                details.append({
                    "citation_number": citation_number,
                    "verified": False,
                    "flagged_text": claims[0],
                    "chunk_id": chunk_id,
                })
                flagged_count += 1

        return {
            "total_citations": len(citations),
            "verified_count": verified_count,
            "flagged_count": flagged_count,
            "details": details,
        }
