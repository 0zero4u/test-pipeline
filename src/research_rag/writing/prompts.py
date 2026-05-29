"""Academic prose prompts for chapter writing."""

SYSTEM_PROMPT = """You are a humanities dissertation writing assistant. Generate formal academic prose for dissertation chapters.

STYLE REQUIREMENTS:
- Third-person academic voice (avoid "I", "we", "you")
- Present tense for literary analysis ("Singh portrays", "the novel demonstrates")
- Past tense for historical context ("The Partition occurred", "violence erupted")
- Formal vocabulary, no contractions
- Each paragraph must have a clear topic sentence
- Use transitions between paragraphs ("Furthermore", "Moreover", "In contrast")
- Analyze, don't summarize — interpret evidence, don't just report it
- Maintain argumentative coherence throughout

CITATION FORMAT:
- Use [N] markers where N is the citation number
- Every claim must be supported by at least one citation
- Paraphrase evidence, don't quote excessively (max 1-2 short quotes per paragraph)
- Page numbers: [N, p. 45] format

DO NOT:
- Add unsupported claims
- Use first-person voice
- Include bullet points or lists (use flowing prose)
- Summarize without analysis
- Introduce new arguments in conclusions"""


def build_section_prompt(
    section_title: str,
    section_description: str,
    evidence_chunks: list[dict],
    chapter_context: str = "",
    previous_sections: str = "",
    target_words: int = 1500,
) -> list[dict]:
    """Build messages for generating a dissertation section.

    Args:
        section_title: Title of the section (e.g., "3.1 Historical Violence in the Novel")
        section_description: Description of what to cover
        evidence_chunks: List of dicts with keys: text, title, page, author, year
        chapter_context: Brief context about the chapter's overall argument
        previous_sections: Summary of previously written sections for coherence
        target_words: Approximate word count target

    Returns:
        List of message dicts for LLM.
    """
    evidence_text = ""
    for i, chunk in enumerate(evidence_chunks, 1):
        author = chunk.get("author", "Unknown")
        year = chunk.get("year", "n.d.")
        title = chunk.get("title", "Unknown")
        page = chunk.get("page", "?")
        text = chunk.get("text", "")
        evidence_text += f"\n[{i}] {text}\n    Source: {author} ({year}), {title}, p. {page}\n"

    user_prompt = f"""Write the following dissertation section in formal academic prose.

SECTION: {section_title}
DESCRIPTION: {section_description}
TARGET LENGTH: Approximately {target_words} words

{f"CHAPTER CONTEXT: {chapter_context}" if chapter_context else ""}

{f"PREVIOUS SECTIONS SUMMARY (maintain coherence): {previous_sections}" if previous_sections else ""}

EVIDENCE FROM SOURCE MATERIALS:
{evidence_text}

INSTRUCTIONS:
1. Write a complete academic section with introduction, body paragraphs, and transition to next section
2. Every claim must cite at least one source using [N] markers
3. Analyze the evidence — don't just summarize
4. Use formal academic prose throughout
5. Include topic sentences and transitions
6. End with a transition to the next section (if applicable)

Write the section now:"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_chapter_outline_prompt(
    chapter_title: str,
    chapter_description: str,
    sections: list[dict],
) -> list[dict]:
    """Build messages for generating a chapter outline.

    Args:
        chapter_title: Title of the chapter
        chapter_description: Description of what the chapter covers
        sections: List of section dicts with keys: title, description

    Returns:
        List of message dicts for LLM.
    """
    sections_text = ""
    for sec in sections:
        sections_text += f"- {sec['title']}: {sec['description']}\n"

    user_prompt = f"""Generate a detailed outline for a dissertation chapter.

CHAPTER: {chapter_title}
DESCRIPTION: {chapter_description}

SECTIONS:
{sections_text}

Create a structured outline with:
1. Chapter introduction paragraph (2-3 sentences)
2. For each section: 3-5 key points to cover
3. Chapter conclusion paragraph (2-3 sentences)
4. Suggested flow and transitions between sections

Return as structured text with clear headings."""

    return [
        {"role": "system", "content": "You are an academic outline generator. Create structured, detailed outlines for dissertation chapters."},
        {"role": "user", "content": user_prompt},
    ]


def build_works_cited_prompt(
    citations: list[dict],
) -> list[dict]:
    """Build messages for generating Works Cited in MLA format.

    Args:
        citations: List of citation dicts with keys: author, title, year, journal, page, source_file

    Returns:
        List of message dicts for LLM.
    """
    citations_text = ""
    for cit in citations:
        author = cit.get("author", "Unknown")
        title = cit.get("title", "Unknown")
        year = cit.get("year", "n.d.")
        journal = cit.get("journal", "")
        page = cit.get("page", "")
        citations_text += f"- {author}. \"{title}.\" {journal} ({year}). p. {page}\n"

    user_prompt = f"""Format these sources into a proper MLA 9th Edition Works Cited page.

SOURCES:
{citations_text}

MLA FORMAT RULES:
- Alphabetical by author last name
- Hanging indent (first line flush, subsequent lines indented)
- Author Last, First format
- Article titles in "quotation marks"
- Book/journal titles in italics
- Year in parentheses after title
- Page numbers with "pp." for ranges, "p." for single pages
- "n.d." if no date available

Generate the Works Cited page:"""

    return [
        {"role": "system", "content": "You are an MLA formatting expert. Generate perfectly formatted Works Cited pages."},
        {"role": "user", "content": user_prompt},
    ]
