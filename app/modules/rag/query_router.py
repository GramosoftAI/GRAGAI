import re
import logging
import json
from enum import Enum
from typing import Dict, Any, Optional

from app.core.llm.deepinfra_llm import DeepInfraLLMClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class SearchType(Enum):
    GRAPH_COMPLETION = "GRAPH_COMPLETION"   # Standard RAG
    CHUNK_SEARCH = "CHUNK_SEARCH"           # Direct fact lookup (Vector only)
    GRAPH_SUMMARY = "GRAPH_SUMMARY"         # High-level overview
    CHAIN_OF_THOUGHT = "CHAIN_OF_THOUGHT"   # Complex reasoning/analysis
    MEMORY_ONLY = "MEMORY_ONLY"             # Personal preferences/chat history
    ENTITY_CONNECTION = "ENTITY_CONNECTION" # How A relates to B
    SOCIAL = "SOCIAL"                       # Greetings, small talk, polite interaction

class QueryRouter:
    """
    Professional Multi-Stage Query Router.
    
    STAGE 1: Regex Pattern Matching (Zero Latency)
    STAGE 2: Semantic Intent Classification (LLM-based, only if Stage 1 is ambiguous)
    """
    
    def __init__(self):
        # Pre-compile regex patterns for high performance
        self.patterns = {
            SearchType.GRAPH_SUMMARY: re.compile(
                r'\b(summarize|summary|overview|tldr|briefly explain|main points|give me a breakdown|tell me everything about)\b', 
                re.IGNORECASE
            ),
            SearchType.CHUNK_SEARCH: re.compile(
                r'\b(email|address|phone|who is|what is the name|exact quote|define|definition|where is|when did|what is the price|percentage)\b', 
                re.IGNORECASE
            ),
            SearchType.CHAIN_OF_THOUGHT: re.compile(
                r'\b(why did|how did|what influenced|explain the reasoning|step by step|compare|contrast|analyze|pros and cons)\b', 
                re.IGNORECASE
            ),
            SearchType.MEMORY_ONLY: re.compile(
                r'\b(what did i say|remember|preferences|previously|earlier|last time|my style)\b',
                re.IGNORECASE
            ),
            SearchType.ENTITY_CONNECTION: re.compile(
                r'\b(connection between|how is .* related to|relation|link between)\b',
                re.IGNORECASE
            ),
            SearchType.SOCIAL: re.compile(
                r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening|how are you|who are you|thanks|thank you|bye|goodbye|help)\b',
                re.IGNORECASE
            )
        }
        self.llm_client = DeepInfraLLMClient()

    async def route_query(self, query: str) -> SearchType:
        """
        Routes the query using a professional hybrid approach.
        """
        # --- STAGE 1: REGEX (Zero Latency) ---
        for search_type, pattern in self.patterns.items():
            if pattern.search(query):
                logger.info(f" Router Stage 1: Regex match -> {search_type.name}")
                return search_type

        # --- STAGE 2: SEMANTIC LLM CLASSIFICATION (High Intelligence) ---
        # Only triggered for complex or ambiguous queries to save tokens
        if len(query.split()) > 5:
            logger.debug(" Router Stage 1 inconclusive. Escalating to Stage 2 (LLM)...")
            try:
                return await self._llm_classify(query)
            except Exception as e:
                logger.warning(f" Router Stage 2 failed: {e}. Falling back to default.")
        
        # Default fallback
        return SearchType.GRAPH_COMPLETION

    async def _llm_classify(self, query: str) -> SearchType:
        """
        Use LLM to determine the user's intent for complex queries.
        """
        prompt = f"""Classify the user's search intent into exactly one category.

CATEGORIES:
- CHUNK_SEARCH: Direct fact lookup (e.g., "What is John's email?")
- GRAPH_SUMMARY: Requests for overviews (e.g., "Tell me about Project X")
- CHAIN_OF_THOUGHT: Complex reasoning (e.g., "Compare these two candidates")
- MEMORY_ONLY: Personal history/preferences (e.g., "What did we decide earlier?")
- ENTITY_CONNECTION: Relationship between two things (e.g., "How is Amit linked to Sarah?")
- SOCIAL: Greetings, thanks, or small talk (e.g., "Hi", "How are you?")
- GRAPH_COMPLETION: General knowledge questions.

QUERY: {query}

Return ONLY the category name."""

        response = await self.llm_client.generate(
            prompt=prompt,
            system_prompt="You are a query routing engine. Return only the category name.",
            temperature=0.0,
            max_tokens=20
        )
        
        category = response.strip().upper()
        try:
            return SearchType(category)
        except ValueError:
            logger.warning(f" LLM returned invalid category: {category}")
            return SearchType.GRAPH_COMPLETION
