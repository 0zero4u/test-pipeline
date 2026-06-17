"""Prompt templates for answer synthesis."""

SYNTHESIS_SYSTEM_PROMPT = """You are a research assistant synthesizing academic evidence. Your role is to provide accurate, citation-grounded answers using ONLY the evidence provided below.

RULES:
1. ONLY use the evidence provided in the numbered sources below.
2. Cite sources using [1], [2], etc. at the relevant claim.
3. If the evidence is insufficient to fully answer, say so.
4. Do NOT make up facts, claims, or citations not in the evidence.
5. Be concise but thorough — cover all relevant evidence.
6. Keep the same language as the question (e.g. if asked in English, answer in English).
"""


def build_synthesis_messages(
    query: str,
    evidence_texts: list[tuple[str, str, int, str]],
    system_prompt: str = SYNTHESIS_SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    """Build the message list for a synthesis LLM call.

    Args:
        query: The user's research question.
        evidence_texts: List of (text, title, page, document_id) tuples.
        system_prompt: System prompt to use.

    Returns:
        List of message dicts for the LLM API.
    """
    evidence_blocks = []
    for i, (text, title, page, doc_id) in enumerate(evidence_texts, 1):
        excerpt = text.strip()
        source_line = f"Source: {title}"
        if page:
            source_line += f", Page {page}"
        evidence_blocks.append(f"[{i}] {excerpt}\n    {source_line}")

    evidence_section = "\n\n".join(evidence_blocks)

    user_content = (
        f"EVIDENCE:\n{evidence_section}\n\n"
        f"QUESTION: {query}\n\n"
        f"Answer the question using ONLY the evidence above. "
        f"Cite sources as [1], [2], etc.\n"
        f"IMPORTANT: Use EXACTLY [N] format for citations.\n"
        f"CORRECT: This is a key finding [1].\n"
        f"INCORRECT: This is a key finding [1, p. 2].\n"
        f"Do NOT include page numbers inside the brackets.\n"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
