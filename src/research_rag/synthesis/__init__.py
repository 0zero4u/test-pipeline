"""Answer synthesis for Research RAG."""

from research_rag.synthesis.client import SynthesisClient
from research_rag.synthesis.generator import AnswerGenerator
from research_rag.synthesis.prompts import SYNTHESIS_SYSTEM_PROMPT

__all__ = ["SynthesisClient", "AnswerGenerator", "SYNTHESIS_SYSTEM_PROMPT"]
