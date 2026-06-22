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
    ORGANIZATION_SPECIFIC = "ORGANIZATION_SPECIFIC" # Pricing, services, location
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"       # "Summarize this document"
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE" # "What is diabetes"
    SUPPORT_INTENT = "SUPPORT_INTENT"       # Complaints, human assistance
    RECENT_EMAILS = "RECENT_EMAILS"         # Queries asking for recent or latest emails
    EMAIL_ANALYSIS = "EMAIL_ANALYSIS"       # Needs gmail/outlook data
    DOCUMENT_QA = "DOCUMENT_QA"             # Questions about documents
    DATA_ANALYSIS = "DATA_ANALYSIS"         # Analysis of data/numbers
    SUMMARIZATION = "SUMMARIZATION"         # Requesting summaries
    TABLE_ANALYTICS = "TABLE_ANALYTICS"     # SQL-like database filtering on structured tables
    EXTRACTIVE = "EXTRACTIVE"               # Exact value extraction (e.g., GSTIN, PAN)

class RouteResult:
    def __init__(self, intent: SearchType, confidence: float, reason: str = "", rewritten: dict = None):
        self.intent = intent
        self.confidence = confidence
        self.reason = reason
        self.rewritten = rewritten or {}
class QueryRouter:
    """
    Professional Multi-Stage Query Router.
    
    STAGE 1: Regex Pattern Matching (Zero Latency)
    STAGE 2: Semantic Intent Classification (LLM-based, only if Stage 1 is ambiguous)
    """
    
    def __init__(self):
        # Pre-compile regex patterns for high performance
        self.patterns = {
            SearchType.EXTRACTIVE: re.compile(
                r'\b(gstin|pan number|pan|invoice number|vin|engine number|address|email|phone|part number|hsn code|customer details|billing address|shipping address|place of delivery|place of supply|registration number)\b',
                re.IGNORECASE
            ),
            SearchType.TABLE_ANALYTICS: re.compile(
                r'\b(below|above|greater than|less than|between|top \d+|highest|lowest|average|count|sum|total of|cheapest|most expensive|all products where|price under|price over|mrp)\b',
                re.IGNORECASE
            ),
            SearchType.SUPPORT_INTENT: re.compile(
                r'\b(help|support|complaint|human|call me|contact support|representative|agent|operator)\b',
                re.IGNORECASE
            ),
            SearchType.RECENT_EMAILS: re.compile(
                r'\b(latest|recent|today|last|newest|today\'s) (mail|email|message|inbox)s?\b',
                re.IGNORECASE
            ),
            SearchType.ORGANIZATION_SPECIFIC: re.compile(
                r'\b(services?|pricing|cost|charges?|fee|staff|policies|contact|location|appointments?|book|products?|operations?)\b',
                re.IGNORECASE
            ),
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
                r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening|how are you|who are you|thanks|thank you|bye|goodbye)\b',
                re.IGNORECASE
            )
        }
        self.llm_client = DeepInfraLLMClient()

    async def route_query(self, query: str) -> RouteResult:
        """
        Routes the query using a professional hybrid approach.
        """
        # --- STAGE 0: QUERY REWRITING ---
        rewritten = await self.rewrite_query(query)
        logger.info(f" Router Stage 0: Rewritten query metadata: {rewritten}")

        # --- STAGE 1: REGEX (Zero Latency) ---
        for search_type, pattern in self.patterns.items():
            if pattern.search(query):
                logger.info(f" Router Stage 1: Regex match -> {search_type.name}")
                return RouteResult(intent=search_type, confidence=1.0, reason="Regex match", rewritten=rewritten)

        # --- STAGE 2: SEMANTIC LLM CLASSIFICATION (High Intelligence) ---
        # Only triggered for complex or ambiguous queries to save tokens
        if len(query.split()) > 2:
            logger.debug(" Router Stage 1 inconclusive. Escalating to Stage 2 (LLM)...")
            try:
                return await self._llm_classify(query, rewritten)
            except Exception as e:
                logger.warning(f" Router Stage 2 failed: {e}. Falling back to default.")
        
        # Default fallback
        return RouteResult(intent=SearchType.GRAPH_COMPLETION, confidence=0.5, reason="Default fallback", rewritten=rewritten)

    async def rewrite_query(self, query: str) -> dict:
        """
        Extracts keywords, entities, and intent for better downstream retrieval.
        """
        prompt = f"""
Rewrite this query for RAG retrieval.
Extract:
- entities
- dates
- intent
- keywords

Query:
{query}

Return ONLY valid JSON in this exact format, with no markdown formatting or backticks:
{{
 "keywords": ["keyword1"],
 "entities": ["entity1"],
 "date_filter": "yesterday",
 "intent": "find information"
}}
"""
        try:
            result = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a query rewriting engine. Return only JSON.",
                temperature=0.0,
                max_tokens=1024
            )
            # Clean up markdown if present
            cleaned = result.replace('```json', '').replace('```', '').strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Failed to rewrite query: {e}")
            return {"keywords": [], "entities": [], "date_filter": "", "intent": ""}

    async def _llm_classify(self, query: str, rewritten: dict) -> RouteResult:
        """
        Use LLM to determine the user's intent for complex queries.
        """
        prompt = f"""
You are an enterprise RAG router.
Analyze:
1. What does user want?
2. Which data source is required?
3. Is reasoning needed?

Choose exactly one of the following intents:
- EMAIL_ANALYSIS: needs gmail/outlook data (e.g., "What did John send me?", "emails about payment")
- RECENT_EMAILS: queries asking for recent or latest emails specifically
- DOCUMENT_QA: Questions about documents
- DATA_ANALYSIS: Analysis of data/numbers
- SUMMARIZATION: Requesting summaries
- SUPPORT_INTENT: Requests requiring human assistance (e.g., "I need help", "How do I contact support", "I have a complaint")
- ORGANIZATION_SPECIFIC: Questions about the organization (e.g., "What services do you provide?", "How can I book an appointment?", "What are your consultation fees?")
- KNOWLEDGE_BASE: Document specific questions (e.g., "Summarize this document", "What does the policy say")
- GENERAL_KNOWLEDGE: Questions unrelated to the organization (e.g., "What is diabetes", "Who invented the internet")
- CHUNK_SEARCH: Direct fact lookup (e.g., "What is John's email?")
- GRAPH_SUMMARY: Requests for overviews (e.g., "Tell me about Project X")
- CHAIN_OF_THOUGHT: Complex reasoning (e.g., "Compare these two candidates")
- MEMORY_ONLY: Personal history/preferences (e.g., "What did we decide earlier?")
- ENTITY_CONNECTION: Relationship between two things (e.g., "How is Amit linked to Sarah?")
- SOCIAL: Greetings, thanks, or small talk (e.g., "Hi", "How are you?")
- TABLE_ANALYTICS: Database-style filtering on tables or price lists (e.g., "Products below 5000", "Top 10 highest MRP", "Average cost")
- EXTRACTIVE: Strict exact value retrieval without generation (e.g., "Give me the GSTIN", "What is the invoice number")
- GRAPH_COMPLETION: General default.

Return ONLY valid JSON in this exact format, with no markdown formatting or backticks:
{{
 "intent": "EMAIL_ANALYSIS",
 "confidence": 0.95,
 "reason": "short explanation"
}}

Query:
{query}
"""

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are an enterprise RAG router. Return only JSON.",
                temperature=0.0,
                max_tokens=1024
            )
            cleaned = response.replace('```json', '').replace('```', '').strip()
            data = json.loads(cleaned)
            
            intent_str = data.get("intent", "GRAPH_COMPLETION").upper()
            try:
                intent = SearchType(intent_str)
            except ValueError:
                intent = SearchType.GRAPH_COMPLETION
                
            return RouteResult(
                intent=intent,
                confidence=float(data.get("confidence", 0.5)),
                reason=data.get("reason", "Parsed from LLM"),
                rewritten=rewritten
            )
        except Exception as e:
            logger.warning(f" LLM classification failed: {e}")
            return RouteResult(intent=SearchType.GRAPH_COMPLETION, confidence=0.0, reason=f"Error: {str(e)}", rewritten=rewritten)
